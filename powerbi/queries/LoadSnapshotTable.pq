// Power Query function: name this query LoadSnapshotTable.
// Create SnapshotId as a text parameter pinned to a verified current.json snapshot value.
// Never resolve current.json independently inside each table query.
(file as text, columnTypes as list) as table =>
let
    Allowed = {"FactEvent.csv","FactSession.csv","FactPayment.csv","FactDailyUser.csv","DimDate.csv","DimCustomer.csv","DimCurrency.csv","FactProductView.csv","DimProduct.csv"},
    Id = SnapshotId,
    ValidId = Text.Length(Id) = 64 and Text.Select(Id, {"0".."9","a".."f"}) = Id,
    Checked = if ValidId and List.Contains(Allowed,file) then file else error "Invalid snapshot or table",
    Raw = if SnapshotRoot <> "" then File.Contents(SnapshotRoot & "/" & Id & "/" & Checked) else Web.Contents("https://raw.githubusercontent.com", [RelativePath="gurusumiran25/pulseforge/main/data/bi/" & Id & "/" & Checked]),
    Parsed = Csv.Document(Raw,[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Parsed,[PromoteAllScalars=true]),
    Expected = List.Transform(columnTypes, each _{0}),
    Schema = if List.Sort(Table.ColumnNames(Headers)) = List.Sort(Expected) then Headers else error "Snapshot schema mismatch",
    Typed = Table.TransformColumnTypes(Schema,columnTypes,"en-US")
in
    Typed
