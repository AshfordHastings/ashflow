from flask import Blueprint, request, jsonify 
from db import get_db_session
from db.db_ops import get_wiki_pages, delete_wiki_page

flashcard_bp = Blueprint("flashcard_bp", __name__)

