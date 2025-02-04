from fastapi import FastAPI
from .database import init_db
from .auth import router as auth_router
from .superuser import router as superuser_router
from .umbrellas import router as umbrellas_router
from .blocks import router as blocks_router
from .zones import router as zones_router
from .members import router as members_router



app = FastAPI(title="TabPay API")


@app.on_event("startup")
async def on_startup():
    await init_db()


app.include_router(auth_router.router)
app.include_router(superuser_router.router)
app.include_router(umbrellas_router.router)
app.include_router(blocks_router.router)
app.include_router(zones_router.router)
app.include_router(members_router.router)


#TODOcheck for duplicates




