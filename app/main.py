from fastapi import FastAPI
from .database import lifespan
from .auth import router as auth_router
from .superuser import router as superuser_router
from .umbrellas import router as umbrellas_router
from .blocks import router as blocks_router
from .zones import router as zones_router
from .members import router as members_router
from .banks import router as banks_router




app = FastAPI(lifespan=lifespan, title="TabPay API")



app.include_router(auth_router.router)
app.include_router(superuser_router.router)
app.include_router(umbrellas_router.router)
app.include_router(blocks_router.router)
app.include_router(zones_router.router)
app.include_router(members_router.router)
# app.include_router(banks_router.router)


#TODOcheck for duplicates




