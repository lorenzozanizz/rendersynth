# Blender Extension Setup

## Installation Steps

### Download from release

1. **Pick a release** 
   - From the Github repository, select a release version
   - Locate the ext.zip file and download it
   
3. **Install in Blender**
   - Open Blender (4.5+ required for the extension)
   - Go to **Edit → Preferences → Get Extensions**
   - Click the **⋮** (three dots) in top-right → **Install from Disk**
   - Select your `.zip` file
   - Enable the extension by toggling the checkbox

4. **Access the extension**
   - Find it in the 3D Viewport sidebar (**N** key)
   - Or check the location specified in the extension's documentation


### Download latest branch from repository

1. **Download the extension**
   - Clone or download this repository (https://github.com/lorenzozanizz/synth-blender-dataset)
   - Locate the `/ext/` folder in the repo

2. **Create a ZIP archive**
   - Compress the **contents** of the `/ext/` folder as a `.zip` file
   - ⚠️ Important: The zip should contain the extension files directly, NOT a folder named "ext". Blender requires the extension to be packed into a zip containing the source code directly. 
   - Correct structure: `extension.zip` > `__init__.py`, etc.
   - Wrong structure: `extension.zip` > `ext/` → files

3. **Install in Blender**
   - Open Blender (4.5+ required for the extension)
   - Go to **Edit → Preferences → Get Extensions**
   - Click the **⋮** (three dots) in top-right → **Install from Disk**
   - Select your `.zip` file
   - Enable the extension by toggling the checkbox

4. **Access the extension**
   - Find it in the 3D Viewport sidebar (**N** key)
   - Or check the location specified in the extension's documentation

## Requirements

- **Blender**: 4.5.0 or later

## Troubleshooting

- **"Not a valid extension"**: Make sure the zip contains files directly, not an `ext/` folder
- **Extension doesn't appear**: Check **Edit > Preferences > Extensions** and verify it's enabled
- **Errors on enable**: Check the Blender **System Console**