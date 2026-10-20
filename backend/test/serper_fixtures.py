# File path: backend/test/serper_fixtures.py
"""
Search results shaped like the real thing. The Instagram formats are the
page descriptions Instagram itself publishes (which Google shows as the
snippet); the reel and the Feedspot list are copied from the search output
in your own earlier run.
"""

PROFILE_VANI = {
    "title": "Vani Mir (@vanimir) • Instagram photos and videos",
    "link": "https://www.instagram.com/vanimir/",
    "snippet": "96K Followers, 1,203 Following, 842 Posts - See Instagram photos and videos from Vani Mir (@vanimir)",
}

PROFILE_RITU_WITH_BIO = {
    "title": "Ritu Jain (@ritujain) • Instagram photos and videos",
    "link": "https://www.instagram.com/ritujain/",
    "snippet": '94.2K Followers, 310 Following, 1,540 Posts - Ritu Jain (@ritujain) on Instagram: "Fashion & beauty creator | OOTD | Delhi 📍"',
}

PROFILE_TOO_BIG = {
    "title": "Mrunal Panchal (@mrunu) • Instagram photos and videos",
    "link": "https://www.instagram.com/mrunu/",
    "snippet": "6.1M Followers, 412 Following, 3,001 Posts - See Instagram photos and videos from Mrunal Panchal (@mrunu)",
}

PROFILE_TOO_SMALL = {
    "title": "New Creator (@newcreator) • Instagram photos and videos",
    "link": "https://www.instagram.com/newcreator/",
    "snippet": "850 Followers, 90 Following, 40 Posts - See Instagram photos and videos from New Creator (@newcreator)",
}

# Handle is in the address, but the snippet says nothing about followers.
POST_NO_COUNT = {
    "title": 'Aditi Banerjee on Instagram: "Monsoon makeup look"',
    "link": "https://www.instagram.com/aditi_banerjee/reel/DQWtutVkYxK/",
    "snippet": '1,234 likes, 56 comments - aditi_banerjee on October 1, 2025: "Monsoon makeup look".',
}

# From your earlier run: a reel with NO handle in its address.
REEL_WITHOUT_HANDLE = {
    "title": "Yay ! 🥳 #100kfollowers #instainfluencer #delhibeautyblogger",
    "link": "https://www.instagram.com/reel/DP6Kh_cki3W/",
    "snippet": "Finally reached 100k ・ 1,075 posts 100K followers 1,598. GIRL -INDIAN Beauty,Fastion&LifestyleCreator ・ 1,075 posts 100K followers 1,598",
}

# From your earlier run: a list page. Snippets show only the biggest accounts.
FEEDSPOT_LIST = {
    "title": "Top 80 Indian Beauty Influencers in 2026",
    "link": "https://influencers.feedspot.com/indian_beauty_instagram_influencers/",
    "snippet": "1. Nagma Mirajkar · @nagmamirajkar Instagram Followers 8.1M Follower Growth (3mo) -1% ; 2. Mrunal Panchal · @mrunu Instagram Followers 6.1M ; 3.",
}

# A list-style page for mid-sized creators.
LIST_MID_SIZE = {
    "title": "Best micro fashion influencers in India",
    "link": "https://example-blog.test/micro-fashion-influencers",
    "snippet": "1. Kavya Rao · @kavyarao Instagram Followers 45.3K ; 2. Isha Nair · @ishanair Instagram Followers 61K ;",
}

# Not a creator at all.
NOISE = {
    "title": "How to find an Instagram profile URL",
    "link": "https://www.youtube.com/watch?v=yIQO4SB48qw",
    "snippet": "Here's how to find an Instagram profile url so you can see an easy way to share someone's profile.",
}

MENTION_WITHOUT_COUNT = {
    "title": "Tips from a blogger",
    "link": "https://example-blog.test/tips",
    "snippet": "Follow @examplehandle for daily tips, and email me@gmail.com with questions.",
}