import os
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import img2pdf
from pdf2image import convert_from_path

# Configuration
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

# Get the absolute path of the directory where this script is located
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Explicitly tell Flask where to find templates and static files
app = Flask(__name__, template_folder=os.path.join(APP_ROOT, 'templates'), static_folder=os.path.join(APP_ROOT, 'static'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.secret_key = 'supersecretkey' # Change this in a real application

# Helper function to check allowed file extensions
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Create necessary folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    """Renders the main page with upload forms."""
    return render_template('index.html')

@app.route('/image-to-pdf', methods=['POST'])
def image_to_pdf():
    """Handles image to PDF conversion."""
    if 'images' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    files = request.files.getlist('images')
    image_paths = []
    
    for file in files:
        if file.filename == '':
            flash('No selected file')
            return redirect(url_for('index'))
        
        if file and allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_paths.append(filepath)
        else:
            flash('Allowed image types are png, jpg, jpeg')
            return redirect(url_for('index'))

    if not image_paths:
        flash('No valid images uploaded.')
        return redirect(url_for('index'))

    # Convert images to PDF
    pdf_filename = "converted_from_images.pdf"
    pdf_path = os.path.join(app.config['CONVERTED_FOLDER'], pdf_filename)
    
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(image_paths))

    # Clean up uploaded images
    for path in image_paths:
        os.remove(path)

    return render_template('index.html', pdf_download_link=pdf_filename)

@app.route('/pdf-to-image', methods=['POST'])
def pdf_to_image():
    """Handles PDF to image conversion."""
    if 'pdf' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['pdf']

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename, ALLOWED_PDF_EXTENSIONS):
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)

        # Convert PDF to images
        try:
            images = convert_from_path(pdf_path, output_folder=app.config['CONVERTED_FOLDER'], fmt='jpeg', output_file="page")
            image_filenames = [os.path.basename(img.filename) for img in images]
        except Exception as e:
            flash(f"An error occurred during PDF conversion: {e}")
            return redirect(url_for('index'))
        finally:
            # Clean up uploaded PDF
            os.remove(pdf_path)

        return render_template('index.html', image_download_links=image_filenames)
    else:
        flash('Allowed file type is pdf')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    """Serves files from the converted folder for download."""
    new_filename = request.args.get('new_filename')
    # If a new filename is provided, use it for the download.
    # Otherwise, the browser will use the original filename.
    return send_from_directory(
        app.config['CONVERTED_FOLDER'],
        filename,
        as_attachment=True,
        download_name=new_filename
    )

if __name__ == '__main__':
    app.run(debug=True)
