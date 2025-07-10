# Rescue MXF corrupted files

Tools for recovering damaged `.mxf` video files.

The disk with video files was formatted. The files obtained using the file recovery program were damaged and were not displayed correctly in the video editor.

## Structure of the MXF file

  By analyzing the correct file (with the same settings as the damaged ones), the file structure (for these settings) was revealed.
  
  | Field          | Size      | KLV                                                                             |
  | :------------: | :-------: | :-----------------------------------------------------------------------------: |
  | `FILE_HEADER`  | `11264`   | `06` `0E` `2B` `34` `02` `05` `01` `01` `0D` `01` `02` `01` `01` `02` `04` `00` |
  | `FRAME_HEADER` | `512`     | `06` `0E` `2B` `34` `02` `05` `01` `01` `0D` `01` `03` `01` `04` `01` `01` `00` |
  | `FRAME_DATA`   | `7452672` | `06` `0E` `2B` `34` `01` `02` `01` `06` `0E` `06` `0D` `03` `19` `01` `45` `00` |
  | `FRAME_FOOTER` | `36352`   | `06` `0E` `2B` `34` `01` `02` `01` `01` `0D` `01` `03` `01` `16` `04` `03` `00` |
  | `FILE_FOOTER`  | `10800`   | `06` `0E` `2B` `34` `02` `05` `01` `01` `0D` `01` `02` `01` `01` `04` `04` `00` |
  
  The header and footer were extracted from the correct file to `header.mxf` `footer.mxf` files
  
## Recovery method
  
  A damaged file may be missing any of its parts. Typically, the beginning of the file is missing (file header and first few frames). In a damaged file, whole frames are searched for (frames that have all parts present: frame header, frame data and frame footer). All found whole frames are written to the output file. After this, the header and footer of the file from the sample files (`header.mxf` `footer.mxf`) are added to the output file. In the header and footer of the output file, the metadata fields (number of frames, timestamp) are set in accordance with the values relevant for the given file.

## Disk scan
  
  On the selected disk (in the direct data reading mode from the disk) the search for whole frames is performed. The found consecutive frames are saved in a separate output file on another selected disk.