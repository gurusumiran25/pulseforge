# Date intelligence and observed cohort retention

Create a contiguous DimDate query by replacing its import expression with:

```powerquery
let
    Source = LoadSnapshotTable("DimDate.csv", {{"date_utc", type date}}),
    Start = List.Min(Source[date_utc]),
    Finish = List.Max(Source[date_utc]),
    Dates = List.Dates(Start, Duration.Days(Finish-Start)+1, #duration(1,0,0,0)),
    Result = Table.TransformColumnTypes(Table.FromList(Dates, Splitter.SplitByNothing(), {"date_utc"}), {{"date_utc", type date}})
in Result
```

Mark DimDate as the date table. Create each measure separately.

```dax
Daily Active Customers = DISTINCTCOUNT(FactDailyUser[user_id])
Rolling 7 Day Sessions = 
    VAR EndDate = MAX(DimDate[date_utc])
    VAR StartDate = EndDate - 6
    RETURN IF(StartDate >= CALCULATE(MIN(DimDate[date_utc]), REMOVEFILTERS(DimDate)),
        DIVIDE(CALCULATE([Sessions], REMOVEFILTERS(DimDate), DATESBETWEEN(DimDate[date_utc], StartDate, EndDate)), 7))
Prior Window Sessions =
    VAR StartDate = MIN(DimDate[date_utc])
    VAR EndDate = MAX(DimDate[date_utc])
    VAR Days = DATEDIFF(StartDate, EndDate, DAY)+1
    RETURN IF(COUNTROWS(VALUES(DimDate[date_utc])) = Days && StartDate-Days >= CALCULATE(MIN(DimDate[date_utc]), REMOVEFILTERS(DimDate)),
        CALCULATE([Sessions], REMOVEFILTERS(DimDate), DATESBETWEEN(DimDate[date_utc], StartDate-Days, StartDate-1)))
Session Growth = DIVIDE([Sessions]-[Prior Window Sessions], [Prior Window Sessions])
```

Cohort retention: create disconnected CohortDay table using GENERATESERIES(1,7,1). Select exactly one cohort date using DimDate and one offset using CohortDay. First observed activity within the snapshot defines membership, not acquisition. Suppress immature cohorts.

```dax
Observed Cohort Retention =
    VAR C = SELECTEDVALUE(DimDate[date_utc])
    VAR N = SELECTEDVALUE(CohortDay[Value])
    VAR LastDate = CALCULATE(MAX(DimDate[date_utc]), REMOVEFILTERS(DimDate))
    VAR Members = FILTER(VALUES(DimCustomer[user_id]),
        CALCULATE(MIN(FactDailyUser[date_utc]), REMOVEFILTERS(DimDate)) = C)
    VAR Returned = FILTER(Members,
        CALCULATE(COUNTROWS(FactDailyUser), REMOVEFILTERS(DimDate), DimDate[date_utc] = C+N) > 0)
    RETURN IF(NOT ISBLANK(C) && NOT ISBLANK(N) && C+N <= LastDate, DIVIDE(COUNTROWS(Returned), COUNTROWS(Members)))
```

Native engine tests pending. A missing activity date is treated as zero only within a verified complete snapshot. Use cohort offsets 1, 3 and 7 for report cards.
