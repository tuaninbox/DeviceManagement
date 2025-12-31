from . import models
from fastapi import FastAPI
from . import database
from app.routers import devices, modules
from strawberry.fastapi import GraphQLRouter
from .graphql import schema

# Create DB tables
# This line tells SQLAlchemy:
# Look at all ORM models that inherit from Base
# Create the corresponding tables in the database if they don’t exist
# This runs once at startup.
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Device Management Backend App")

# Register endpoints with the app
# REST routers
app.include_router(devices.router)
app.include_router(modules.router)

# GraphQL endpoint
# app.include_router(graphql_app, prefix="/graphql")

# GraphQL resolvers often need access to:
# - The database session
# - The current user
# - Request metadata
# This function creates a fresh DB session for each GraphQL request.
def get_context():
    db = database.SessionLocal()
    return {"db": db}

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")

# Define root router
@app.get("/")
def root():
    # return {"message": "Device Management API is running"}
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
