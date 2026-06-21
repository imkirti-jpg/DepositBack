from pydantic import BaseModel

class PreferencesResponse(BaseModel):
    email_enabled: bool
    sms_enabled: bool

class PreferencesUpdate(BaseModel):
    email_enabled: bool
    sms_enabled: bool