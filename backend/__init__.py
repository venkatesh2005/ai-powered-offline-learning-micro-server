# Offline AI-Powered Learning Hub
# Version 1.0.0
# 
# A complete offline e-learning platform with AI capabilities
# Built with Flask, GPT4All, FAISS, and SQLite

__version__ = '1.0.0'
__author__ = 'Your Name'
__description__ = 'Offline AI-Powered Learning Hub'

# Quick reference for imports
from app import app
from config import Config
from database.models import db, User, Resource, Quiz, QuizResult, Notification, ChatHistory
