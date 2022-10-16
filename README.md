# ARM Template Dependencies Graph Validator
Converts an ARM Template dependencies to a directed Graph and validates it

## How to Run?
### JSON
Used for single ArmTemplate inspection.
1. Place the ArmTemplate json to inspect in the same folder with "main.py"
1. Run ```main.py <file-name>.json```

### Csv
Used for multiple ArmTemplates.
Expecting structure: Timestamp,GUID,ArmTemplate
1. Place the ArmTemplate csv to inspect in the same folder with "main.py"
1. Run ```main.py <file-name>.csv```
