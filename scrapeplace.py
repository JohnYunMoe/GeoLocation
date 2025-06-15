### INITIAL CODE TO TEST GOOGLE PLACES API
### DID NOT WORK, ATTEMPTING NORMAL SCRAPING INSTEAD
# Google Places API Key
PLACES_API_KEY = "AIzaSyCX1rGcLozrKgWkNn-IEVLg0U4z8PaYr1A"

import requests
import json

url = "https://places.googleapis.com/v1/places:searchText"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": PLACES_API_KEY,
    "X-Goog-FieldMask": "places.id,places.displayName"
}
data = {
    "textQuery": "Restaurants in San Francisco"
}

response = requests.post(url, headers=headers, json=data)
results = response.json()
print(results)

####### NEW CODE THAT USES PAGINATION ####### 

# import requests
# import time
# import json

# def search_places(query, max_results=100):
#     url = "https://places.googleapis.com/v1/places:searchText"
#     headers = {
#         "Content-Type": "application/json",
#         "X-Goog-Api-Key": "YOUR_API_KEY",
#         "X-Goog-FieldMask": "places.id,nextPageToken"  # Include nextPageToken for pagination
#     }
    
#     data = {
#         "textQuery": "Restaurants in San Francisco"
#     }
    
#     all_places = []
#     page_count = 0
    
#     # First request
#     response = requests.post(url, headers=headers, json=data)
#     results = response.json()
    
#     # Add places from first page
#     if "places" in results:
#         all_places.extend(results["places"])
#         page_count += 1
#         print(f"Retrieved page {page_count} with {len(results['places'])} places")
    
#     # Continue fetching next pages while we have a nextPageToken
#     # and haven't reached our maximum desired results
#     while "nextPageToken" in results and len(all_places) < max_results:
#         # The API requires a short delay before using the nextPageToken
#         time.sleep(2)
        
#         # Update the request with the nextPageToken
#         data["pageToken"] = results["nextPageToken"]
        
#         # Make the next request
#         response = requests.post(url, headers=headers, json=data)
#         results = response.json()
        
#         # Add places from this page
#         if "places" in results:
#             all_places.extend(results["places"])
#             page_count += 1
#             print(f"Retrieved page {page_count} with {len(results['places'])} places")
    
#     print(f"Total places retrieved: {len(all_places)}")
#     return all_places

# # Example usage
# places = search_places("Restaurants in San Francisco", max_results=60)



