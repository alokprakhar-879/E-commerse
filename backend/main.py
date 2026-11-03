import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.database import engine, Base
from backend.routers import categories, products, customers, orders, reports, inventory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify/create tables on startup (idempotent; schema.sql handles initial PostgreSQL DDL)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Notice: Table creation / verification check: {e}")
    yield

app = FastAPI(
    title="E-Commerce & Inventory Management System API",
    description="Full-stack DBMS backend demonstrating ACID transactions, concurrency control, 3NF schema, and relational analytics.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React dev servers (standard ports: 3000, 5173, etc.)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(orders.router)
app.include_router(reports.router)
app.include_router(inventory.router)

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "E-Commerce & Inventory Management API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
