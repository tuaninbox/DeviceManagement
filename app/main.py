from .models import devices
from fastapi import FastAPI
from .databases import devices
from app.routers import devices, modules, jobs
from strawberry.fastapi import GraphQLRouter
from .graphql import schema
from fastapi.middleware.cors import CORSMiddleware

# Create DB tables
# This line tells SQLAlchemy:
# Look at all ORM models that inherit from Base
# Create the corresponding tables in the database if they don’t exist
# This runs once at startup.
devices.Base.metadata.create_all(bind=devices.engine)

app = FastAPI(title="Device Management Backend App")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],          # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],          # allow all headers
)


# Register endpoints with the app
# REST routers
app.include_router(devices.router)
app.include_router(modules.router)
app.include_router(jobs.router)

# GraphQL endpoint
# app.include_router(graphql_app, prefix="/graphql")

# GraphQL resolvers often need access to:
# - The database session
# - The current user
# - Request metadata
# This function creates a fresh DB session for each GraphQL request.
def get_context():
    db = devices.SessionLocal()
    return {"db": db}

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")

# Define root router
@app.get("/")
def root():
    # return {"message": "Device Management API is running"}
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
