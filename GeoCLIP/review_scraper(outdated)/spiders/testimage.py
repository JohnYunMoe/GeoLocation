import re
import os
import shutil
import requests
from bs4 import BeautifulSoup
from scrapy.http import HtmlResponse

class ImageScrapingTester:
    def __init__(self):
        self.HEADERS = {
            "Authorization": "Bearer 5dbe9addb2ae9bec756198b7c71a1fd54330c0e8915caedbb77108c928e1ba42",
            "Content-Type": "application/json"
        }
        
    def download_image(self, name, url):
        """Helper method to download images from a url"""
        try:
            print(f"DEBUG: Attempting to download {name} from {url}")
            
            # Clean up the URL - remove quotes if present
            url = url.strip('"\'')
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            if not os.path.exists("./test_images"):
                os.makedirs("./test_images")
                
            file_path = f"./test_images/{name}.png"
            with open(file_path, "wb") as out_file:
                shutil.copyfileobj(response.raw, out_file)
                
            print(f"DEBUG: Successfully saved {file_path} ({os.path.getsize(file_path)} bytes)")
            return True
            
        except Exception as e:
            print(f"DEBUG: Failed to download image {name}: {e}")
            return False

    def test_image_scraping_from_fid(self, feature_id):
        """Test image scraping for a specific restaurant feature_id"""
        
        # Construct the Google reviews URL
        url = f"https://www.google.com/async/reviewDialog?async=feature_id:{feature_id},next_page_token:,_fmt:pc"
        
        print(f"DEBUG: Testing URL: {url}")
        
        # Make request using BrightData proxy
        data = {
            "zone": "isp_proxy1",
            "url": url,
            "format": "raw"
        }

        response = requests.post(
            "https://api.brightdata.com/request",
            json=data,
            headers=self.HEADERS,
        )
        
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response length: {len(response.text)}")
        
        # Convert to Scrapy response for XPath parsing
        scrapy_response = HtmlResponse(url=url, body=response.content, encoding='utf-8')
        
        # Debug: Save the HTML to file for inspection
        with open("debug_response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("DEBUG: Saved response HTML to debug_response.html for inspection")
        
        # Find all reviews
        all_reviews = scrapy_response.xpath('//*[@id="reviewSort"]/div/div[2]/div')
        print(f"DEBUG: Found {len(all_reviews)} reviews")
        
        if not all_reviews:
            # Try alternative selector
            all_reviews = scrapy_response.xpath('//div[contains(@class, "review")]')
            print(f"DEBUG: Found {len(all_reviews)} reviews with alternative selector")
        
        total_images_found = 0
        
        for review_idx, review in enumerate(all_reviews[:3]):  # Test first 3 reviews only
            print(f"\nDEBUG: Processing review {review_idx + 1}")
            
            # Get reviewer info
            reviewer = review.css("div.TSUbDb a::text").extract_first()
            reviewer_id = review.xpath(
                "substring-before(substring-after(.//div[@class='TSUbDb']/a[contains(@href, '/maps/contrib/')]/@href, '/contrib/'), '?')"
            ).extract_first()
            
            print(f"DEBUG: Reviewer: {reviewer}, ID: {reviewer_id}")
            
            # Try multiple image selectors
            selectors = [
                './/div[@class="EDblX GpHuwc"]/div/a/div',  # Original
                './/div[contains(@class, "EDblX")]/div/a/div',  # More flexible
                './/div[contains(@style, "background-image")]',  # Look for background images
                './/div[contains(@style, "url(")]',  # Look for any URL in style
                './/div[@class="EDblX GpHuwc"]//div[@style]',  # Look for styled divs within image containers
            ]
            
            review_imgs_div = []
            for selector in selectors:
                review_imgs_div = review.xpath(selector)
                print(f"DEBUG: Selector '{selector}' found {len(review_imgs_div)} images")
                if review_imgs_div:
                    break
            
            if not review_imgs_div:
                print("DEBUG: No images found with any selector, trying broader search...")
                # Get all divs with style attributes to debug
                all_styled_divs = review.xpath('.//div[@style]')
                print(f"DEBUG: Found {len(all_styled_divs)} divs with style attributes")
                
                for i, div in enumerate(all_styled_divs[:5]):  # Show first 5
                    style = div.xpath('@style').extract_first()
                    print(f"DEBUG: Style {i+1}: {style}")
                continue
            
            # Process images
            url_pattern = re.compile(r"url\((.*?)\)")
            
            for img_idx, review_img_div in enumerate(review_imgs_div):
                if img_idx >= 3:  # Limit to 3 images per review for testing
                    break
                    
                style_str = review_img_div.xpath("@style").extract_first()
                print(f"DEBUG: Image {img_idx + 1} style: {style_str}")
                
                if not style_str:
                    print("DEBUG: No style attribute found")
                    continue
                
                # Extract URL
                url_match = url_pattern.search(style_str)
                if not url_match:
                    print("DEBUG: No URL found in style string")
                    continue
                    
                url = url_match.group(1)
                print(f"DEBUG: Original URL: {url}")
                
                # Modify URL for higher resolution
                url = re.sub(r"=w100-h100-p-n-k-no", "", url)
                url += "=s1000-no"
                print(f"DEBUG: Modified URL: {url}")
                
                # Create image name
                feature_id_str = feature_id.replace(":", "_")
                image_name = f"test_{feature_id_str}_{reviewer_id or 'unknown'}_{img_idx + 1}"
                
                # Download image
                success = self.download_image(image_name, url)
                if success:
                    total_images_found += 1
                    
        print(f"\nDEBUG: Total images downloaded: {total_images_found}")
        return total_images_found

# Test with a specific restaurant
if __name__ == "__main__":
    tester = ImageScrapingTester()
    
    # Replace this with a feature_id from your restaurant_details.json
    test_fid = input("Enter a feature_id to test (from your restaurant_details.json): ").strip()
    
    if test_fid:
        images_found = tester.test_image_scraping_from_fid(test_fid)
        print(f"\nTest completed. Found and attempted to download {images_found} images.")
        print("Check the './test_images/' folder and 'debug_response.html' file for results.")
    else:
        print("No feature_id provided. Exiting.")