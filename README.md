I want to build a device management web app that has 2 components

# Backend - API
- Using FastAPI Framework
- Use SQL Lite for the moment, but may upgrade to other database later
- Authentication using LDAP for now, but can upgrade to SSO Later
- Support GraphQL
- Data return as JSON format or any other better format?

# Frontend
- Written in FastAPI as well
- Authentication using LDAP, but will upgrade to SSO later, pass JWT to Backend

# Database
- Run as SQL Lite, but upgrade to other later


## Schema
- Device has the following data
  - hostname
  - management address
    - vrf
  - location (from snmp)
  - group
  - uptime
  - model
  - serial number
  - software information
    - OS version
    - Firmware version
    - last updated
    - vulnerability
  - modules
    - description
    - part number
    - serial number
    - warranty from (if any)
    - warranty expiry
    - environment status (if any)
    - last updated
  - interfaces
    - name
    - status
    - description
    - last updated
    - sfp (link to modules if available)
      - description
      - part number
      - serial number
    - vrf
    - last updated
  - running configuration
    - last updated
    - updated by (if available)
  - operational data
    - routing table
      - vrf (if available else default)
    - mac address table
      - vrf (if available else default)
    - vlan
      - id
      - name
      - membership
      - last updated
  - last updated

  
# Running the app
1. Project Folder
```
device_management/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── crud.py
├── routers/
│   ├── devices.py
│   ├── modules.py
│   └── __init__.py
├── graphql.py
└── __init__.py
```

2. Installation
- pip install fastapi uvicorn sqlalchemy strawberry-graphql

3. Database Setup
In database.py, configure SQLite (already provided).

Later, swap the connection string for PostgreSQL/MySQL when upgrading.

4. Define Models
- Define how data is stored in the database
- In models.py, add SQLAlchemy ORM models (Device, Module, Interface, etc.).
- Run models.Base.metadata.create_all(bind=database.engine) in main.py to auto‑create tables.

5. Define Schema
- Define how data is validated and returned in API responses.
- Schemas do NOT affect the database. They only affect:
  - Request validation
  - Response serialization
- In schemas.py, add Pydantic models for request/response validation.
- Include orm_mode = True so SQLAlchemy objects can be returned directly.

6. CRUD Functions
In crud.py, implement helper functions (create, get, list, update).

These keep DB logic separate from API routes.

7. Routers
In routers/devices.py, add REST endpoints for devices.

In routers/modules.py, add endpoints for modules.

You can extend with more routers (interfaces, configs, etc.).

8. GraphQL Integration
In graphql.py, define Strawberry types (DeviceType, ModuleType).

Add resolvers for queries (e.g., list devices).

Mount with GraphQLRouter(schema) in main.py.

9. Main Application
In main.py, include routers and GraphQL:

```
app.include_router(devices.router)
app.include_router(modules.router)
app.include_router(graphql_app, prefix="/graphql")
```

10. Run the app
- uvicorn device_management.main:app --reload
- REST API: http://127.0.0.1:8000/devices
- GraphQL Playground: http://127.0.0.1:8000/graphql

11. Quick Test
- REST: POST /devices with JSON body:
```
`json
{
  "hostname": "router1",
  "mgmt_address": "10.0.0.1",
  "model": "Cisco 9300",
  "serial_number": "ABC123"
}
```
- using curl
```
curl -X POST http://127.0.0.1:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"query { devices { id hostname mgmtAddress model serialNumber } }"}'

curl -X POST http://127.0.0.1:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { addDevice(hostname:\"router3\", mgmtAddress:\"10.0.0.3\", model:\"Cisco 4451\", serialNumber:\"DEF456\") { id hostname mgmtAddress } }"}'

```
- GraphQL: Query in Playground:
```
graphql
query {
  devices {
    id
    hostname
    mgmtAddress
    modules {
      description
      partNumber
    }
  }
}
```