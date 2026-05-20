from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ VERY IMPORTANT (allow frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Sample restaurant API
@app.get("/restaurants")
def get_restaurants():
    return [
        {"name": "Pizza Hub", "cuisine": "Italian", "rating": 4.5},
        {"name": "Biryani House", "cuisine": "Indian", "rating": 4.7},
        {"name": "Burger King", "cuisine": "Fast Food", "rating": 4.2},
        {"name": "Sushi World", "cuisine": "Japanese", "rating": 4.8},
        {"name": "Taco Fiesta", "cuisine": "Mexican", "rating": 4.3},
        {"name": "Cafe Coffee Day", "cuisine": "Cafe", "rating": 4.1},
        {"name": "BBQ Nation", "cuisine": "Grill", "rating": 4.6},
    ]
