# Blender Mosaic Effect Add-on

A Blender add-on that applies a real-time mosaic (pixelation) effect to selected 3D models during rendering.

## Features

- ✅ **Shader-based effect** - True real-time mosaic rendering (not post-processing)
- ✅ **Works with animation** - Effect follows models through camera movement and animation
- ✅ **Adjustable mosaic size** - Control pixelation intensity (2-200)
- ✅ **Simple UI** - Easy-to-use panel in the 3D viewport sidebar
- ✅ **Multiple objects** - Apply effect to multiple models simultaneously
- ✅ **Enable/Disable toggle** - Quick on/off control

## Installation

1. **Download the add-on file**: `mosaic_effect_addon.py`

2. **Open Blender** (version 3.0 or higher)

3. **Install the add-on**:
   - Go to `Edit` → `Preferences` → `Add-ons`
   - Click `Install...` button
   - Navigate to and select `mosaic_effect_addon.py`
   - Click `Install Add-on`

4. **Enable the add-on**:
   - Search for "Mosaic Effect" in the add-ons list
   - Check the checkbox to enable it

## Usage

### Accessing the Panel

1. In the 3D Viewport, press `N` to open the sidebar
2. Click on the `Mosaic` tab

### Applying the Effect

1. **Select one or more mesh objects** in your scene
2. In the Mosaic panel, click **"Add Selected Objects"**
3. The mosaic effect is now applied to those objects

### Adjusting Mosaic Size

1. Change the **"Mosaic Size"** value (2-200)
   - Lower values = less pixelation (larger blocks)
   - Higher values = more pixelation (smaller blocks)
2. Click the **refresh icon** next to the slider to update all targets

### Removing the Effect

- **Remove specific objects**: Select them and click **"Remove Selected Objects"**
- **Remove all**: Click **"Clear All"**

### Enable/Disable

- Use the **"Enable Effect"** checkbox to toggle the effect on/off without removing targets

## How It Works

The add-on uses Blender's shader node system to create a true mosaic effect:

1. **Texture Coordinates** - Uses object-space coordinates
2. **Pixelation Math** - Multiplies coordinates by mosaic size, floors the values, then divides back
3. **Shader Application** - Applies an emission shader with the pixelated color
4. **Real-time Rendering** - Works in Eevee and Cycles render engines

This approach ensures:
- The effect renders correctly in animations
- Camera movement doesn't affect the mosaic pattern
- Lighting and shadows work properly
- No post-processing required

## Technical Details

### Shader Node Setup

```
Texture Coordinate (Object) 
  → Multiply (by mosaic_size)
  → Floor
  → Divide (by mosaic_size)
  → Separate XYZ
  → Combine XYZ
  → Emission Shader
  → Material Output
```

### Material Naming

Materials are automatically named as `Mosaic_{ObjectName}` to avoid conflicts.

## Limitations

- Only works with mesh objects
- Replaces the first material slot (or adds a new one if empty)
- Effect is based on object coordinates (not UV mapping)

## Troubleshooting

**Effect not visible:**
- Ensure you're in Material Preview or Rendered viewport shading mode
- Check that "Enable Effect" is checked
- Verify the object is in the targets list

**Effect looks wrong:**
- Try adjusting the mosaic size
- Ensure the object has proper scale (apply scale with Ctrl+A if needed)

**Effect doesn't update:**
- Click the refresh icon after changing mosaic size
- Re-add the object if issues persist

## Compatibility

- **Blender Version**: 3.0 or higher
- **Render Engines**: Eevee, Cycles
- **Operating Systems**: Windows, macOS, Linux

## Uninstallation

1. Go to `Edit` → `Preferences` → `Add-ons`
2. Find "Mosaic Effect"
3. Click the checkbox to disable
4. Click the `Remove` button

## License

Free to use and modify for personal and commercial projects.
