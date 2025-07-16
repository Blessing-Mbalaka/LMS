import os
import docx
import docx2txt
import shutil
import subprocess

def extract_images_with_emf_fallback(docx_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    doc = docx.Document(docx_path)
    rels = doc.part._rels

    extracted_images = []
    failed_images = []

    for rel in rels:
        rel_obj = rels[rel]
        if "image" in rel_obj.target_ref:
            try:
                img_data = rel_obj.target_part.blob
                img_filename = os.path.basename(rel_obj.target_ref)
                img_path = os.path.join(output_folder, img_filename)

                with open(img_path, "wb") as f:
                    f.write(img_data)

                print(f"[✓] Extracted image: {img_filename}")
                extracted_images.append(img_filename)
            except Exception as e:
                print(f"[✗] Failed to extract image: {rel_obj.target_ref} - {e}")
                failed_images.append(rel_obj.target_ref)

    if failed_images:
        choice = input("Some images failed to extract. Try EMF fallback? (y/n): ")
        if choice.lower() != "y":
            print("Skipping fallback.")
            return

        fallback_folder = os.path.join(output_folder, "emf_fallback")
        os.makedirs(fallback_folder, exist_ok=True)
        docx2txt.process(docx_path, fallback_folder)

        for filename in os.listdir(fallback_folder):
            if filename.lower().endswith(".emf"):
                emf_path = os.path.join(fallback_folder, filename)
                png_path = os.path.join(output_folder, filename.replace(".emf", ".png"))
                convert_emf_to_png(emf_path, png_path)
                print(f"[✓] Fallback EMF converted to PNG: {png_path}")
            elif filename not in extracted_images:
                fallback_file_path = os.path.join(fallback_folder, filename)
                shutil.copy(fallback_file_path, output_folder)
                print(f"[✓] Copied fallback file: {filename}")

def convert_emf_to_png(emf_path, output_path):
    try:
        subprocess.run(["magick", emf_path, output_path], check=True)
    except Exception as e:
        print(f"[✗] Failed to convert EMF: {emf_path} - {e}")
