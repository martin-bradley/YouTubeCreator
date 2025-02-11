import praw
import boto3
import subprocess
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
import os
from dotenv import load_dotenv
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import date
import re

def fetch_reddit_posts():
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         user_agent=os.getenv('REDDIT_USER_AGENT'))
    top_posts = reddit.subreddit('todayilearned').top(time_filter='day', limit=30)
    return top_posts

def extract_keywords(title):
    common_words = {'is', 'and', 'but', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'as', 'of'}
    words = re.findall(r'\b\w+\b', title.lower())
    keywords = [word for word in words if word not in common_words]
    return keywords

def generate_audio(polly, post_text, post_id):
    try:
        ssml_text = f"<speak><prosody rate='medium'>{post_text}</prosody></speak>"
        response = polly.synthesize_speech(Text=ssml_text, TextType='ssml', OutputFormat='mp3', VoiceId='Matthew')
        audio_filename = f"/path/to/{post_id}.mp3"
        with open(audio_filename, 'wb') as file:
            file.write(response['AudioStream'].read())
        print(f"Generated audio: {audio_filename}")
        return audio_filename
    except Exception as e:
        print(f"Error generating audio for post {post_id}: {e}")
        return None

def generate_video(post_text, audio_filename, post_id, background_video_path):
    try:
        if not os.path.exists(background_video_path):
            raise FileNotFoundError(f"{background_video_path} file not found.")
        video = VideoFileClip(background_video_path)

        # Get the duration of the audio file
        audio = AudioFileClip(audio_filename)
        audio_duration = audio.duration

        # Get the duration of the background video
        video_duration = video.duration

        # Set the duration of the text clip and video based on audio duration + 4 seconds margin
        text_duration = audio_duration + 4
        txt_clip = TextClip(text=post_text, 
                            font='Futura', 
                            size=(700, 1454),  
                            font_size=30,
                            margin=(50,0),      
                            color='white',
                            stroke_color='black',
                            stroke_width=2, 
                            method='caption',  
                            text_align='center',
                            horizontal_align='center', 
                            vertical_align='center',
                            duration=video_duration)

        # Composite the video and text
        text_video = CompositeVideoClip([video, txt_clip])

        temp_video_filename = f"/path/to/{post_id}_temp.mp4"
        text_video.write_videofile(temp_video_filename, fps=24)

        # Combine the audio with the video
        output_file = f"/path/to/{post_id}.mp4"
        subprocess.run([
            "ffmpeg", "-i", temp_video_filename, "-i", audio_filename, "-filter_complex",
            "[1:a]adelay=2000|2000[a1];[0:a][a1]amix=inputs=2:duration=first[a]", "-map", "0:v", "-map", "[a]", 
            "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", output_file])
        print(f"Generated video: {output_file}")
        os.remove(temp_video_filename)
        os.remove(audio_filename)
    except Exception as e:
        print(f"Error generating video for post {post_id}: {e}")

def upload_video_to_youtube(video_file, title, description, category_id=22, privacy_status="public"):
    try:
        credentials = get_credentials()
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # Extract keywords from the Reddit title
        keywords = extract_keywords(title)
        
        # Initialize the video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['shorts', 'today i learned', 'interesting', 'fact', 'short facts'] + keywords,  # Add more tags if needed
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False,
            }
        }
        # Upload the video
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
        )
        response = request.execute()
        print(f"Uploaded video ID: {response['id']}")
    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("/path/to/credentials.json", ["https://www.googleapis.com/auth/youtube.upload"])
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def read_processed_post_ids(file_path):
    try:
        with open(file_path, 'r') as file:
            return set(line.strip() for line in file)
    except FileNotFoundError:
        return set()

def write_processed_post_id(file_path, post_id):
    with open(file_path, 'a') as file:
        file.write(post_id + '\n')

def main():
    load_dotenv()  # Load environment variables from .env file

    try:
        processed_posts_file = '/path/to/processed_posts.txt'
        processed_post_ids = read_processed_post_ids(processed_posts_file)

        posts = fetch_reddit_posts()
        if not posts:
            print("No suitable posts found.")
            return

        polly = boto3.client('polly', region_name='eu-west-2')
        
        background_videos = [
            '/path/to/background6.mp4',
            '/path/to/background7.mp4',
            '/path/to/background8.mp4',
            '/path/to/background9.mp4',
            '/path/to/background10.mp4'
        ]

        video_count = 0
        today = date.today().strftime("%B %d, %Y")
        for post in posts:
            if video_count >= 10:
                break

            if post.id in processed_post_ids:
                print(f"Skipping already processed post ID: {post.id}")
                continue

            post_content = post.title
            print(f"Post Title: {post.title}")
            print(f"Post Content: {post_content}")

            audio_filename = generate_audio(polly, post_content, post.id)
            if audio_filename:
                background_video_path = background_videos[video_count % len(background_videos)]
                generate_video(post_content, audio_filename, post.id, background_video_path)
                video_file = f"/path/to/{post.id}.mp4"
                # Update the video title
                video_title = f"Today I Learnt - {today} - {video_count + 1}"
                upload_video_to_youtube(video_file, video_title, post.title)
                write_processed_post_id(processed_posts_file, post.id)
                video_count += 1

    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
