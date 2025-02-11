# YouTube Shorts from Reddit Automation

## Overview

This project automates the process of creating YouTube shorts from Reddit posts. It leverages various libraries such as `praw`, `boto3`, `moviepy`, and `googleapiclient` to fetch Reddit posts, process video content, and upload the final videos to YouTube.

## Features

- **Automated Fetching:** Uses `praw` to fetch the latest and most popular posts from specified Reddit subreddits.
- **Video Processing:** Utilizes `moviepy` to create engaging video content from the fetched Reddit posts.
- **Cloud Storage Integration:** Employs `boto3` for securely storing video content on AWS S3.
- **YouTube Integration:** Integrates with YouTube Data API using `googleapiclient` to upload videos directly to your YouTube channel.
- **Scheduled Runs:** Configured to run daily without manual intervention, ensuring a constant stream of fresh content.

## Requirements

- Python 3.6+
- `praw` library
- `boto3` library
- `moviepy` library
- `googleapiclient` library
