from app.databases.users import SessionLocal
from app.models.users import UserProfile
from datetime import datetime, timezone

def ensure_user_profile(username: str, full_name: str = None, email: str = None):
    """
    Ensures a UserProfile exists for the given username.
    If it exists, optionally updates fields.
    If not, creates a new profile.
    """
    db = SessionLocal()

    profile = db.query(UserProfile).filter(UserProfile.username == username).first()

    if not profile:
        profile = UserProfile(
            username=username,
            full_name=full_name,
            email=email
        )
        db.add(profile)
        db.commit()
        return profile

    # Update existing profile if new info is provided
    updated = False

    if full_name and profile.full_name != full_name:
        profile.full_name = full_name
        updated = True

    if email and profile.email != email:
        profile.email = email
        updated = True
    
    # Always update last_login 
    profile.last_login = datetime.now(timezone.utc)
    updated = True

    if updated:
        db.commit()

    return profile
