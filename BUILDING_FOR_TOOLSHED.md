# Building the Toolshed wheel with ChimeraX 1.12

This is a **source bundle**, not a prebuilt wheel. Build the distributable wheel with ChimeraX's bundle builder so the required `ChimeraX :: Bundle` classifier is generated.

1. Extract this folder to a path without spaces, for example `H:\vina\myTools\ChimeraX-VinaGridBox-v1.9.1-source`.
2. Open ChimeraX 1.12 and run:

   ```text
   devel clean H:/vina/myTools/ChimeraX-VinaGridBox-v1.9.1-source
   devel build H:/vina/myTools/ChimeraX-VinaGridBox-v1.9.1-source
   ```

3. The resulting wheel is placed under that folder's `dist` directory. Use the newly created wheel, not an older wheel copied from another directory.
4. Inspect the wheel as a ZIP archive. In `ChimeraX_VinaGridBox-1.9.1.dist-info/METADATA`, confirm there is a line starting with `Classifier: ChimeraX :: Bundle` and that it appears before `Classifier: ChimeraX :: Tool` and `Classifier: ChimeraX :: Command` entries.
5. Test-install that exact wheel in ChimeraX:

   ```text
   toolshed install H:/vina/myTools/ChimeraX-VinaGridBox-v1.9.1-source/dist/ChimeraX_VinaGridBox-1.9.1-py3-none-any.whl
   ```

6. Verify `vinabox set center 0,0,0 size 20,20,20`, `vinabox bounds padding 4`, `vinabox centroid padding 4`, `vinabox report`, `vinabox showgui`, `vinabox hidegui`, `vinabox clear`, and Tools → Binding Analysis → Vina Grid Box.
7. Submit the exact newly built and tested wheel to the ChimeraX Toolshed.

Do **not** build the publishable wheel with `python setup.py bdist_wheel`, `pip wheel`, or another generic Python packaging command. The bundle's `bundle_info.xml` is the source of ChimeraX metadata; ChimeraX's `devel build` / Bundle Builder generates the required base bundle classifier.
