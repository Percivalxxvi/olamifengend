# import email
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from model import User,Login,Post
import os
from dotenv import load_dotenv
from utilities import hashedpassword,verifyHashed
from utilities import send_email,send_html_email
from utilities import generate_otp
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from bson import ObjectId  # to convert string id to MongoDB ObjectId


load_dotenv()

from astrapy import DataAPIClient

# Initialize the client
token_db=os.getenv("DB_TOKEN")
print(token_db)
client = DataAPIClient(token_db)
db = client.get_database_by_api_endpoint(
  "https://4a0ad75e-7212-454a-934f-77360d1f8628-us-east-2.apps.astra.datastax.com"
)
user_collection = db.create_collection("Users")
news_collection = db.create_collection("News")
print(f"Connected to Astra DB: {db.list_collection_names()}")

app=FastAPI()

data={
    1:{"name":"john","age":23},
    2:{"name":"mike","age":25},
    3:{"name":"tobi","age":25},
    4:{"name":"alex","age":45},
    5:{"name":"josh","age":23}
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.delete("/delete_user/{id}")
async def delete_user(id:str):
    
    user=user_collection.find_one({"_id":id})
    if user:
        user_collection.delete_one({"_id":id})
        return JSONResponse(content={"message":"user deleted"},status_code=status.HTTP_200_OK)
    return JSONResponse(content={"message":"user not found"},status_code=status.HTTP_404_NOT_FOUND)

@app.put("/update_user/{id}/{new_name}")
async def update_user(id:str,new_name:str):
    print(id,new_name)
    user=user_collection.find_one({"_id":id})
    if user:
        user_collection.update_one({"_id":id},{"$set":{"name":new_name}})
        return JSONResponse(content={"message":"user updated"},status_code=status.HTTP_200_OK)
    return JSONResponse(content={"message":"user not found"},status_code=status.HTTP_404_NOT_FOUND)


# post
@app.post("/update/")
async def create_user(name:str,id:int,new_name:str):
    for x in data:
        if id == x:
            if data[x]["name"].lower() == name.lower():
                data[x]["name"]=new_name
            return JSONResponse(content={"user":data[x]})
        return JSONResponse(content={"message":"id already exists"})
    else:
        return JSONResponse(content={"message":"user not found"})
    

@app.post("/delete/")
async def delete_user(id:int):
    for x in data:
        if id == x:
            del data[x]
            return JSONResponse(content={"message":"user deleted"})
    return JSONResponse(content={"message":"user not found"})


# @app.delete("/delete_user/{id}")
# async def delete_user(id: int):
#     if id in data:
#         del data[id]
#         return {"success": True, "message": "user deleted"}

#     return {"success": False, "message": "user not found"}

# using pydantic model
@app.post("/create_user/")
async def create_user(user:User):
    data=dict(user)
    data["password"]=hashedpassword(data["password"])
    c=user_collection.insert_one(data)
    print(data,type(data))
    send_html_email(data["email"],"Welcome to Olamifeng",c.inserted_id)
    return JSONResponse(content={"message":"user created successfully","user":data},status_code=status.HTTP_201_CREATED)

@app.get("/verify/")
def verify_user(token:str):
    data = user_collection.find_one({"_id": token})
    if data:
        user_collection.update_one({"_id": token}, {"$set": {"is_active": True}})
        return JSONResponse(content={"message":"user verified","user":data},status_code=status.HTTP_200_OK)
    return JSONResponse(content={"message":"user not found"},status_code=status.HTTP_404_NOT_FOUND)

# @app.post("/login")
# async def login_user(login:Login):
#     data=dict(login)
#     user=user_collection.find_one({"email":data["email"]})
#     if user:
#         try:
#             if verifyHashed(user["password"],data["password"]):
#                 otp = generate_otp()
#                 user=user_collection.find_one_and_update({"email":data["email"]}, {"$set": {"otp": otp}})
#                 send_email(user["email"],"OTP Verification",f"Your OTP code is: {otp}")
#                 return JSONResponse(content={"message":"login successful","user_id":user["_id"]},status_code=status.HTTP_200_OK) 
#         except:
#             return JSONResponse(content={"message":"invalid password"},status_code=status.HTTP_401_UNAUTHORIZED) 
#     return JSONResponse(content={"message":"user not found"},status_code=status.HTTP_404_NOT_FOUND)

# @app.post("/login")
# async def login_user(login: Login):
#     data = dict(login)
#     user = user_collection.find_one({"email": data["email"]})
#     if not user:
#         return JSONResponse({"message": "user not found"}, status_code=404)
    
#     if not verifyHashed(user["password"], data["password"]):
#         return JSONResponse({"message": "invalid password"}, status_code=401)

#     otp = generate_otp()
#     user_collection.find_one_and_update({"email": data["email"]}, {"$set": {"otp": otp}})
    
#     try:
#         send_email(user["email"], "OTP Verification", f"Your OTP code is: {otp}")
#     except Exception as e:
#         print("Failed to send OTP:", e)
#         return JSONResponse({"message": "failed to send OTP"}, status_code=500)

#     return JSONResponse({"message": "login successful", "user_id": user["_id"]}, status_code=200)

@app.post("/login")
async def login_simple(login: Login):
    data = dict(login)
    user = user_collection.find_one({"email": data["email"]})
    
    if not user:
        return JSONResponse({"message": "user not found"}, status_code=status.HTTP_404_NOT_FOUND)
    
    if not verifyHashed(user["password"], data["password"]):
        return JSONResponse({"message": "invalid password"}, status_code=status.HTTP_401_UNAUTHORIZED)
    
    # Return user info without password
    user_info = {k: v for k, v in user.items() if k != "password"}
    
    return JSONResponse(
        {"message": "login successful", "user": user_info},
        status_code=status.HTTP_200_OK
    )

@app.post("/verify_otp/")
def verify_otp(user:dict):
    main_user=user_collection.find_one({"_id":user["id"]})
    if main_user:
        if main_user["otp"]==user["otp"]:
            user_collection.update_one({"_id":user["id"]},{"$set":{"otp":""}})
            return JSONResponse(content={"message":"OTP verified successfully","id":main_user["_id"]},status_code=status.HTTP_200_OK)
        return JSONResponse(content={"message":"invalid OTP"},status_code=status.HTTP_400_BAD_REQUEST)
    return JSONResponse(content={"message":"user not found"},status_code=status.HTTP_404_NOT_FOUND)


@app.post("/password")
def update_password(id:str,password:str):
    user=user_collection.find_one({"_id":id})
    if user:
        user_collection.update_one({"_id":id},{"$set":{"password":password}})
        return JSONResponse(content={"message":"password updated"},status_code=status.HTTP_200_OK)
    return JSONResponse(content={"message":"user not found"},status_code=status.HTTP_404_NOT_FOUND)


# Admin endpoints

@app.get("/all_users")
async def get_all_users():
    users=list(user_collection.find())
    new_users=[]
    for user in users:
        user.pop("password")
        user.pop("message")
        new_users.append(user)
    return JSONResponse(content={"message":"all users fetched","users":new_users},status_code=status.HTTP_200_OK)


@app.post("/create_post/")
async def create_post(post: dict):  # or a Pydantic model
    title = post.get("title")
    body = post.get("body")
    if title and body:
        news_collection.insert_one({"title": title, "body": body})
        return {"message": "post created"}
    return {"message": "missing title or body"}, 400

@app.get("/all_posts")
async def get_all_posts():
    posts = list(news_collection.find())
    return JSONResponse(
        content={"message": "posts fetched", "posts": posts},
        status_code=status.HTTP_200_OK
    )

# delete post by id stored as string
@app.delete("/delete_post/{post_id}")
async def delete_post(post_id: str):
    post = news_collection.find_one({"_id": post_id})  # use string directly
    if post:
        news_collection.delete_one({"_id": post_id})
        return JSONResponse(
            content={"message": "Post deleted successfully"},
            status_code=status.HTTP_200_OK
        )
    return JSONResponse(
        content={"message": "Post not found"},
        status_code=status.HTTP_404_NOT_FOUND
    )

@app.get("/post/{id}")
def get_post(id: str):
    post = news_collection.find_one({"_id": id})
    if post:
        return {"post": post}
    return {"message": "Post not found"}, 404