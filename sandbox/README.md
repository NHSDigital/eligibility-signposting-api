# Sandbox environment

## Developer instructions

Run the following command to start the sandbox environment:

```bash
make spec
make up
```

This will start the sandbox environment on localhost port 5000.

```bash
make down
```

This will stop the sandbox environment.

### Example curl calls

patient 0000000001 is a patient eligible and bookable for a Flu vaccination.

```bash
 curl -X GET "http://0.0.0.0:5000/eligibility?patient=0000000001" -H "Accept: application/json" -H "Authorization: Bearer sdvsd"
```

See [app.py](app.py) for more examples.
