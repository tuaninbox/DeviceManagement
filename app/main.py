from . import models
from fastapi import FastAPI
from . import databases
from app.routers import devices, modules, jobs, auth, commands
from strawberry.fastapi import GraphQLRouter
from .graphql import schema
from fastapi.middleware.cors import CORSMiddleware

from config.auth_loader import get_local_config
from app.models.users import LocalUser
from app.auth.password_utils import hash_password
from app.databases.users import SessionLocal

# from app.models.users import LocalUser, UserProfile

# Create the corresponding tables in the database if they don't exist
# This runs once at startup.
models.devices.Base.metadata.create_all(bind=databases.devices.engine)
models.users.Base.metadata.create_all(bind=databases.users.engine)
#LocalUser.metadata.create_all(bind=databases.users.engine)
models.users.Base.metadata.create_all(bind=databases.users.engine)
#UserProfile.metadata.create_all(bind=users_engine)

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
app.include_router(auth.router)
app.include_router(commands.router) 


# GraphQL endpoint
# app.include_router(graphql_app, prefix="/graphql")

# GraphQL resolvers often need access to:
# - The database session
# - The current user
# - Request metadata
# This function creates a fresh DB session for each GraphQL request.
def get_context():
    db = databases.devices.SessionLocal()
    return {"db": db}

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")


@app.on_event("startup")
def bootstrap_local_admin():
    cfg = get_local_config()
    bootstrap = cfg.get("bootstrap_admin")

    if not bootstrap:
        return

    db = SessionLocal()
    existing = db.query(LocalUser).first()
    if existing:
        return

    admin = LocalUser(
        username=bootstrap["username"],
        password_hash=hash_password(bootstrap["password"]),
        roles="admin"
    )
    db.add(admin)
    db.commit()

# Define root router
@app.get("/")
def root():
    # return {"message": "Device Management API is running"}
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

