import os

class Config:
    pass 

class TestingConfig(Config): 
    TESTING = True 
    DATABASE_URI = "postgresql://postgres:password@localhost:5432/wiki_db"

class DevelopmentConfig(Config): 
    DEBUG = True 
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://postgres:password@db:5432/flashcard_db')
