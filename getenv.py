import os
from customExceptions import BadEnvironmentalVarException
from dotenv import load_dotenv
load_dotenv("secrets.env")

print(os.getenv("token"))

# A checked version of os.getenv that throws a special error when the return value is none.
def getenv(key: str) -> str:
    value = os.getenv(key)
    if value is not None:
        return value
    else:
        raise BadEnvironmentalVarException(key)
