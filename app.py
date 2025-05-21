

import streamlit as st
import base64
import requests
import json
import io
from PIL import Image, ImageDraw, ImageFont

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Creative Generator ✨ (Initial Version) ",
    layout="centered",
    initial_sidebar_state="auto",
)

# --- LinkedIn Profile URL (Replace with your actual LinkedIn URL) ---
LINKEDIN_PROFILE_URL = "https://www.linkedin.com/in/abhishek-kumawat-iitd/" # <-- REPLACE THIS!

# --- How it Works Button ---
if st.button("Feedback?/ How it Works?"):
    st.markdown(f"""
    <a href="{LINKEDIN_PROFILE_URL}" target="_blank">
        <div style="
            display: inline-block;
            padding: 10px 20px;
            background-color: #0077B5; /* LinkedIn blue */
            color: white;
            border-radius: 5px;
            text-align: center;
            text-decoration: none;
            font-weight: bold;
            cursor: pointer;
        ">
            Visit My LinkedIn Profile
        </div>
    </a>
    """, unsafe_allow_html=True)
    st.info("Contact the developer for more details.")


st.header("✨ Creative Generator v1")
st.markdown("Generate user appealing creatives with the `imagen-3.0-generate-002` model.")
st.markdown("---")

# --- API Key Configuration (using Streamlit Secrets) ---
try:
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Gemini API Key not found in Streamlit secrets.")
        st.markdown(
            "Please add your `GEMINI_API_KEY` to your `.streamlit/secrets.toml` file."
        )
        st.stop()
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error(
        f"Error loading Gemini API Key: {e}. Ensure `GEMINI_API_KEY` is in `.streamlit/secrets.toml`."
    )
    st.stop()


# --- User Inputs ---
st.subheader("1. Enter Your Prompt")
prompt_text = st.text_area(
    "Describe the image you want to generate:",
    "A Danish vacation home with pool and people enjoying in summer.",
    height=150,
    help="Provide a detailed description of the image.",
)

st.subheader("2. Upload an Optional Reference Image")
uploaded_image = st.file_uploader(
    "Upload an image (optional, for image-to-image generation):",
    type=["png", "jpg", "jpeg"],
    help="This image will be used as a reference for the generation. If none is uploaded, only the text prompt will be used."
)

st.subheader("3. Specify Image Dimensions")
dimensions_input = st.text_input(
    "Enter desired image dimension (e.g., 768x512):",
    "768x512",
    help="Enter WxH dimension for the base image."
)

st.markdown("---")
st.subheader("4. Customize Overlays (Logo, Coupon, USPs)")

# --- Logo Upload and Position ---
st.markdown("##### Company Logo")
company_logo = st.file_uploader(
    "Upload your company logo (optional):",
    type=["png", "jpg", "jpeg"],
    help="This logo will be placed on the generated image. PNG with transparency is recommended."
)
logo_bg_image = st.file_uploader(
    "Upload Logo Background Image (optional):",
    type=["png", "jpg", "jpeg"],
    help="Optional background image for the logo."
)

logo_position_col1, logo_position_col2 = st.columns(2)
with logo_position_col1:
    logo_x_percent = st.slider("Logo X Position (%)", 0, 100, 5, help="Horizontal position of the logo from the left edge.")
with logo_position_col2:
    logo_y_percent = st.slider("Logo Y Position (%)", 0, 100, 5, help="Vertical position of the logo from the top edge.")

logo_size_percent = st.slider("Logo Size (%)", 1, 30, 15, help="Size of the logo relative to the image width.")


# --- Coupon Configuration ---
st.markdown("##### Coupon Code")
coupon_text = st.text_input("Coupon Text:", "25% discount on vacation homes!")
coupon_bg_image = st.file_uploader(
    "Upload Coupon Background Image (optional):",
    type=["png", "jpg", "jpeg"],
    help="If uploaded, this image will be used as the background for the coupon text."
)
coupon_text_color = st.color_picker("Coupon Text Color:", "#FF0000", help="Choose the color for the coupon text.")
coupon_bg_color = st.color_picker("Coupon Background Color (if no image):", "#FFFFFF", help="Choose the background color for the coupon if no image is uploaded.")

coupon_position_col1, coupon_position_col2 = st.columns(2)
with coupon_position_col1:
    coupon_x_percent = st.slider("Coupon X Position (%)", 0, 100, 50, help="Horizontal position of the coupon unit from the left edge.")
with coupon_position_col2:
    coupon_y_percent = st.slider("Coupon Y Position (%)", 0, 100, 5, help="Vertical position of the coupon unit from the top edge.")

coupon_size_percent = st.slider("Coupon Size (%)", 1, 50, 20, help="Size of the coupon background relative to the image width.")


# --- USP Strip Configuration ---
st.markdown("##### USPs (Unique Selling Propositions)")
usp_list_input = st.text_area(
    "USPs (one per line):",
    "65+ years of experience\nFree Cancellation\n4+ rating on Trustpilot",
    height=100,
    help="Each line will be a separate USP on the bottom strip."
)
usp_list = [usp.strip() for usp in usp_list_input.split('\n') if usp.strip()]
strip_bg_color = st.color_picker("USP Strip Background Color:", "#000000", help="Choose the background color for the USP strip.")
strip_text_color = st.color_picker("USP Strip Text Color:", "#FFFFFF", help="Choose the text color for the USPs.")


# --- Font path (IMPORTANT: You need to provide a valid path to a .ttf font file) ---
# For local testing, put a font file (e.g., Arial.ttf) in the same directory as app.py
# For deployment on Streamlit Cloud, ensure this font file is part of your repo.
FONT_PATH = "2.ttf" # Replace with your actual font file name or path

# Check if font file exists
try:
    ImageFont.truetype(FONT_PATH, 1) # Try loading with a dummy size to check existence
except IOError:
    st.error(f"Error: Font file not found at '{FONT_PATH}'. Please ensure a .ttf font file exists in your project directory.")
    st.stop()


# --- Function to add text overlays ---
def add_overlays_to_image(image_bytes, coupon_text, usps, logo_data=None, logo_pos=(0.05, 0.05), logo_size_perc=0.15,
                           logo_bg_data=None,
                           coupon_bg_image_data=None, coupon_text_color="#FF0000", coupon_bg_color="#FFFFFF",
                           coupon_pos=(0.50, 0.05), coupon_size_perc=0.20,
                           strip_bg_color="#000000", strip_text_color="#FFFFFF", font_path=FONT_PATH):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA") # Ensure RGBA for transparency
    draw = ImageDraw.Draw(img)
    img_width, img_height = img.size

    # --- Company Logo Overlay ---
    # Process logo background first if provided
    if logo_bg_data:
        try:
            logo_bg = Image.open(io.BytesIO(logo_bg_data)).convert("RGBA")
            # Calculate background size based on logo size and a slight padding
            target_bg_width = int(img_width * logo_size_perc * 1.2) # 20% larger than logo
            bg_aspect_ratio = logo_bg.width / logo_bg.height
            target_bg_height = int(target_bg_width / bg_aspect_ratio)
            logo_bg = logo_bg.resize((target_bg_width, target_bg_height), Image.LANCZOS)
            
            # Calculate logo background position (centered around where the logo will be)
            logo_x_px = int(img_width * logo_pos[0])
            logo_y_px = int(img_height * logo_pos[1])

            logo_bg_x = int(logo_x_px - (target_bg_width - int(img_width * logo_size_perc)) / 2)
            logo_bg_y = int(logo_y_px - (target_bg_height - (int(img_width * logo_size_perc) / (logo.width/logo.height) if logo_data else 0)) / 2)

            img.paste(logo_bg, (logo_bg_x, logo_bg_y), logo_bg)
        except Exception as e:
            st.warning(f"Could not place logo background: {e}. Please check the uploaded file.")

    # Process logo itself
    if logo_data:
        try:
            logo = Image.open(io.BytesIO(logo_data)).convert("RGBA")
            # Calculate logo size based on image width percentage
            target_logo_width = int(img_width * logo_size_perc)
            logo_aspect_ratio = logo.width / logo.height
            target_logo_height = int(target_logo_width / logo_aspect_ratio)
            logo = logo.resize((target_logo_width, target_logo_height), Image.LANCZOS)

            # Calculate position
            logo_x = int(img_width * logo_pos[0])
            logo_y = int(img_height * logo_pos[1])

            # Paste logo, handling transparency
            img.paste(logo, (logo_x, logo_y), logo)
        except Exception as e:
            st.warning(f"Could not place logo: {e}. Please check the uploaded logo file.")


    # --- Coupon Code ---
    try:
        coupon_font_size = int(img_height * 0.04) # Adjust size relative to image height
        coupon_font = ImageFont.truetype(font_path, coupon_font_size)
    except IOError:
        st.warning(f"Could not load font for coupon. Using default. Ensure '{font_path}' exists.")
        coupon_font = ImageFont.load_default()
        
    coupon_text_bbox = draw.textbbox((0,0), coupon_text, font=coupon_font)
    coupon_text_width = coupon_text_bbox[2] - coupon_text_bbox[0]
    coupon_text_height = coupon_text_bbox[3] - coupon_text_bbox[1]
    
    # Calculate coupon background size and position
    coupon_bg_width = int(img_width * coupon_size_perc)
    coupon_bg_aspect = 2.5 # Default aspect ratio for coupon background if no image or error
    if coupon_bg_image_data:
        try:
            temp_coupon_bg = Image.open(io.BytesIO(coupon_bg_image_data))
            coupon_bg_aspect = temp_coupon_bg.width / temp_coupon_bg.height
        except:
            pass # Fallback to default aspect if image reading fails
    coupon_bg_height = int(coupon_bg_width / coupon_bg_aspect)

    # Position coupon unit (background + text) based on user input
    coupon_x = int(img_width * coupon_pos[0] - coupon_bg_width / 2) # Center horizontally
    coupon_y = int(img_height * coupon_pos[1] - coupon_bg_height / 2) # Center vertically

    # Calculate text position relative to the coupon background
    coupon_text_x = coupon_x + (coupon_bg_width - coupon_text_width) / 2
    coupon_text_y = coupon_y + (coupon_bg_height - coupon_text_height) / 2


    if coupon_bg_image_data:
        try:
            coupon_bg_img = Image.open(io.BytesIO(coupon_bg_image_data)).convert("RGBA")
            coupon_bg_img = coupon_bg_img.resize((coupon_bg_width, coupon_bg_height), Image.LANCZOS)
            img.paste(coupon_bg_img, (coupon_x, coupon_y), coupon_bg_img)
            draw.text((coupon_text_x, coupon_text_y), coupon_text, font=coupon_font, fill=coupon_text_color)
        except Exception as e:
            st.warning(f"Could not use coupon background image: {e}. Using solid color fallback.")
            draw.rectangle([coupon_x, coupon_y, coupon_x + coupon_bg_width, coupon_y + coupon_bg_height], fill=coupon_bg_color)
            draw.text((coupon_text_x, coupon_text_y), coupon_text, font=coupon_font, fill=coupon_text_color)
    else:
        # Fallback to solid color if no image or error
        draw.rectangle([coupon_x, coupon_y, coupon_x + coupon_bg_width, coupon_y + coupon_bg_height], fill=coupon_bg_color)
        draw.text((coupon_text_x, coupon_text_y), coupon_text, font=coupon_font, fill=coupon_text_color)


    # --- USP Strip ---
    strip_height = int(img_height * 0.15) # 15% of image height for the strip
    draw.rectangle([0, img_height - strip_height, img_width, img_height], fill=strip_bg_color)

    try:
        usp_font_size = int(strip_height / (len(usps) + 1.5)) # Distribute font size based on number of USPs
        if usp_font_size < 10: usp_font_size = 10 # Minimum font size
        usp_font = ImageFont.truetype(font_path, usp_font_size)
    except IOError:
        st.warning(f"Could not load font for USPs. Using default. Ensure '{font_path}' exists.")
        usp_font = ImageFont.load_default()

    # Position USPs vertically
    y_offset = img_height - strip_height + 5 # Start a bit from the top of the strip
    for usp in usps:
        usp_text_bbox = draw.textbbox((0,0), usp, font=usp_font)
        usp_text_width = usp_text_bbox[2] - usp_text_bbox[0]
        
        # Center USP text horizontally
        usp_x = (img_width - usp_text_width) / 2
        draw.text((usp_x, y_offset), usp, font=usp_font, fill=strip_text_color)
        y_offset += usp_font_size + 5 # Move down for next USP with padding

    # Convert back to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()


# --- Generate Button ---
if st.button("🎨 Generate Creative with Overlays"):
    if not prompt_text:
        st.warning("Please enter a text prompt to generate creative.")
        st.stop()

    # Parse the single dimension
    dim_str = dimensions_input.strip()
    if 'x' in dim_str:
        try:
            width, height = map(int, dim_str.split('x'))
        except ValueError:
            st.error(
                f"Invalid dimension format: '{dim_str}'. Please use WxH (e.g., 768x512)."
            )
            st.stop()
    else:
        st.error(
            f"Invalid dimension format: '{dim_str}'. Please use WxH (e.g., 768x512)."
        )
        st.stop()

    st.markdown("---")
    st.subheader("Generated Base Image:")

    base64_image_input = None
    if uploaded_image:
        try:
            image_bytes = uploaded_image.getvalue()
            base64_image_input = base64.b64encode(image_bytes).decode("utf-8")
            st.info("Reference image uploaded and encoded.")
        except Exception as e:
            st.error(f"Error processing uploaded image: {e}")
            st.stop()
            
    # Read company logo bytes
    logo_bytes = None
    if company_logo:
        try:
            logo_bytes = company_logo.getvalue()
        except Exception as e:
            st.warning(f"Could not read company logo: {e}")

    # Read logo background image bytes
    logo_bg_bytes = None
    if logo_bg_image:
        try:
            logo_bg_bytes = logo_bg_image.getvalue()
        except Exception as e:
            st.warning(f"Could not read logo background image: {e}")

    # Read coupon background image bytes
    coupon_bg_image_bytes = None
    if coupon_bg_image:
        try:
            coupon_bg_image_bytes = coupon_bg_image.getvalue()
        except Exception as e:
            st.warning(f"Could not read coupon background image: {e}")


    # Generate the base image from Imagen
    payload = {
        "instances": {"prompt": prompt_text, "width": width, "height": height},
        "parameters": {"sampleCount": 1},
    }

    if base64_image_input:
        payload["instances"]["image"] = {"bytesBase64Encoded": base64_image_input}

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GEMINI_API_KEY}"

    try:
        with st.spinner(f"Generating base image ({width}x{height})..."):
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
            )
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            result = response.json()

            if (
                result.get("predictions")
                and len(result["predictions"]) > 0
                and result["predictions"][0].get("bytesBase64Encoded")
            ):
                initial_generated_image_bytes_b64 = result["predictions"][0]["bytesBase64Encoded"]
                initial_generated_image_bytes = base64.b64decode(initial_generated_image_bytes_b64)
                
                # --- Add Overlays to the base image ---
                post_processed_image_bytes = add_overlays_to_image(
                    initial_generated_image_bytes,
                    coupon_text,
                    usp_list,
                    logo_data=logo_bytes,
                    logo_pos=(logo_x_percent / 100, logo_y_percent / 100), # Convert percentage to ratio
                    logo_size_perc=logo_size_percent / 100, # Convert percentage to ratio
                    logo_bg_data=logo_bg_bytes,
                    coupon_bg_image_data=coupon_bg_image_bytes,
                    coupon_text_color=coupon_text_color,
                    coupon_bg_color=coupon_bg_color,
                    coupon_pos=(coupon_x_percent / 100, coupon_y_percent / 100), # Convert percentage to ratio
                    coupon_size_perc=coupon_size_percent / 100, # Convert percentage to ratio
                    strip_bg_color=strip_bg_color,
                    strip_text_color=strip_text_color
                )
                post_processed_image_b64 = base64.b64encode(post_processed_image_bytes).decode('utf-8')
                post_processed_image_url = f"data:image/png;base64,{post_processed_image_b64}"

                st.image(
                    post_processed_image_url,
                    caption=f"Generated Base Image ({width}x{height}) with Overlays",
                    use_container_width=True,
                )
                st.success(f"Creative generated and processed successfully ({width}x{height})!")

                st.download_button(
                    label=f"Download Creative ({width}x{height}) with Overlays",
                    data=post_processed_image_bytes,
                    file_name=f"base_image_with_overlays_{width}x{height}.png",
                    mime="image/png",
                )
            else:
                st.warning(
                    f"No image data found in the response for base image ({width}x{height}). Response: {result}"
                )

    except requests.exceptions.RequestException as req_err:
        st.error(f"Network or API request error: {req_err}")
        if response.status_code == 400:
            st.error(
                "Bad Request: This might be due to an invalid prompt, unsupported dimensions, or an issue with the reference image."
            )
        elif response.status_code == 403:
            st.error("Forbidden: Check your API key and ensure it has access to the Imagen API.")
        elif response.status_code == 429:
            st.error("Too Many Requests: You've hit a rate limit. Please wait a moment and try again.")
        st.json(response.json())
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

    st.markdown("---")
    st.caption(
        "In development phase: v1"
    )
    
