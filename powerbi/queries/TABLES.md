# Power Query table definitions

Create each named query separately after defining SnapshotId and LoadSnapshotTable. The snapshot must already be published on main. Fixed-decimal amounts require upstream precision validation before release.

## FactEvent

```powerquery
LoadSnapshotTable("FactEvent.csv", {{"event_id", type text}, {"event_name", type text}, {"session_id", type text}, {"user_id", type text}, {"event_time_utc", type datetimezone}, {"date_utc", type date}})
```

## FactSession

```powerquery
LoadSnapshotTable("FactSession.csv", {{"session_id", type text}, {"user_id", type text}, {"first_event_time", type datetimezone}, {"last_event_time", type datetimezone}, {"date_utc", type date}, {"event_count", Int64.Type}, {"viewed_product", Int64.Type}, {"added_to_cart", Int64.Type}, {"started_checkout", Int64.Type}, {"completed_payment", Int64.Type}})
```

## FactPayment

```powerquery
LoadSnapshotTable("FactPayment.csv", {{"event_id", type text}, {"event_name", type text}, {"session_id", type text}, {"user_id", type text}, {"date_utc", type date}, {"currency", type text}, {"amount", Currency.Type}})
```

## FactDailyUser

```powerquery
LoadSnapshotTable("FactDailyUser.csv", {{"date_utc", type date}, {"user_id", type text}, {"sessions", Int64.Type}, {"events", Int64.Type}})
```

## DimDate

```powerquery
LoadSnapshotTable("DimDate.csv", {{"date_utc", type date}})
```

## DimCustomer

```powerquery
LoadSnapshotTable("DimCustomer.csv", {{"user_id", type text}})
```

## DimCurrency

```powerquery
LoadSnapshotTable("DimCurrency.csv", {{"currency", type text}})
```

## FactProductView

```powerquery
LoadSnapshotTable("FactProductView.csv", {{"event_id", type text}, {"session_id", type text}, {"user_id", type text}, {"date_utc", type date}, {"product_id", type text}})
```

## DimProduct

```powerquery
LoadSnapshotTable("DimProduct.csv", {{"product_id", type text}, {"category", type text}})
```
