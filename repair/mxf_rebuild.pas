uses
  System,
  System.IO;


type
  TKey = array of byte;


const
  KEY_SIZE         : int64 = 16;
  LENGTH_SIZE      : int64 = 4;
  
  FILE_HEADER_SIZE : int64 = 11264;
  FILE_FOOTER_SIZE : int64 = 10800;
  
  FRAME_HEADER_SIZE: int64 = 512;
  FRAME_DATA_SIZE  : int64 = 7452672;
  FRAME_FOOTER_SIZE: int64 = 36352;
  
  FILE_HEADER_START : TKey = ($02, $05, $01, $01, $0D, $01, $02, $01, $01, $02, $04, $00);
  //FILE_FOOTER_START : TKey = ($02, $05, $01, $01, $0D, $01, $02, $01, $01, $11, $01, $00);
  FILE_FOOTER_START : TKey = ($02, $05, $01, $01, $0D, $01, $02, $01, $01, $04, $04, $00);
  
  FRAME_HEADER_START: TKey = ($02, $05, $01, $01, $0D, $01, $03, $01, $04, $01, $01, $00);
  FRAME_DATA_START  : TKey = ($01, $02, $01, $06, $0E, $06, $0D, $03, $19, $01, $45, $00);
  FRAME_FOOTER_START: TKey = ($01, $02, $01, $01, $0D, $01, $03, $01, $16, $04, $03, $00);
  
  DURATION_OFFSETS  : array of integer = 
  (
    $0BC8,
    $0C27,
    $0CEF,
    $0D6F,
    $15F2,
    $0E37,
    $0EB7,
    $0F7F,
    $0FFF,
    $10C7,
    $1147,
    $120F,
    $128F,
    $1357,
    $13D7,
    $1593,
    $16BA,
    $173A,
    $1802,
    $1882,
    $194A,
    $19CA,
    $1A92,
    $1B12,
    $1BDA,
    $1C5A,
    $1D22,
    $1DA2
  );


function FindAtomKey(fs: FileStream): boolean;
begin
  var header := 0;
  for var i := 0 to 3 do
    header := (header shl 8) or fs.ReadByte();
  result := header = $060E2B34;
end;

function GetLength(fs: FileStream): longword;
begin
  result := 0;
  for var i := 0 to 3 do
    result := (result shl 8) or fs.ReadByte();
end;

function GetKey(fs: FileStream): array of byte;
begin
  result := new byte[12];
  fs.Read(result, 0, 12);
end;

function KeyCompare(key1, key2: TKey): boolean;
begin
  result := true;
  for var i := 0 to 11 do
    if key1[i] <> key2[i] then
      begin
        result := false;
        break;
      end;
end;

procedure LinePrint(adr: int64; key: array of byte; len: longword; desc: string);
begin
  Console.Write('{0:X16}: ', adr);
  Console.Write('060E2B34');
  for var i := 0 to 11 do
    Console.Write('{0:X2}', key[i]);
  Console.WriteLine(' {0:X8} - {1:s}', len, desc);
end;

procedure AppendHeader(fs: FileStream; pos: int64; count: longword);
begin
  var header := &File.OpenRead('header.mxf');
  var data   := new byte[FILE_HEADER_SIZE];
  header.Read(data, 0, FILE_HEADER_SIZE);
  header.Close();
  
  for var i := 0 to DURATION_OFFSETS.Length-1 do
    begin
      var offset := DURATION_OFFSETS[i];
      var value  := count;
      for var j := 3 downto 0 do
        begin
          data[offset+j] := value;
          value := value shr 8;
        end;
    end;
  
  var start := pos;
  for var i := 7 downto 0 do
    begin
      data[$002C+i] := start;
      start := start shr 8;
    end;
  
  fs.Position := 0;
  fs.Write(data, 0, FILE_HEADER_SIZE);
end;

procedure AppendFooter(fs: FileStream; pos: int64; count: longword);
begin
  var footer := &File.OpenRead('footer.mxf');
  var data   := new byte[FILE_FOOTER_SIZE];
  footer.Read(data, 0, FILE_FOOTER_SIZE);
  footer.Close();
  
  for var i := 0 to DURATION_OFFSETS.Length-1 do
    begin
      var offset := DURATION_OFFSETS[i];
      var value  := count;
      for var j := 3 downto 0 do
        begin
          data[offset+j] := value;
          value := value shr 8;
        end;
    end;
  
  foreach var adr in [$001C, $002C, $2A23] do
    begin
      var start := pos;
      for var i := 7 downto 0 do
        begin
          data[adr+i] := start;
          start := start shr 8;
        end;
    end;
  {var start := fs.Position;
  for var i := 0 to 3 do
    begin
      data[$2A2B-i] := start;
      start := start shr 8;
    end;}
  
  fs.Write(data, 0, FILE_FOOTER_SIZE);
end;

begin
  var args := Environment.GetCommandLineArgs();
  
  var SrcFname := args.Length > 1 ? args[1] : '';
  var DstFname := '';
  
  while not &File.Exists(SrcFname) do
    begin
      Console.Write('file: ');
      SrcFname := Console.ReadLine();
    end;
  
  var dp := SrcFname.LastIndexOf('.');
  DstFname := SrcFname.Substring(0, dp <> -1 ? dp : SrcFname.Length) + '_rebuilt.mxf';
  
  var src := &File.OpenRead(SrcFname);
  var dst := &File.OpenWrite(DstFname);
  
  dst.Position := FILE_HEADER_SIZE;
  
  var FrameRecords := 0;
  var FrameCount   := 0;
  var FrameHeader  := false;
  var FrameBody    := false;
  
  var t0 := DateTime.Now;
  
  while src.Position < src.Length do
    begin
      var offset := src.Position;
      
      if FindAtomKey(src) then
        begin
          var key := GetKey(src);
          var len := GetLength(src);
          
          if KeyCompare(key, FRAME_HEADER_START) then
            begin
              LinePrint(offset, FRAME_HEADER_START, len, 'FRAME_HEADER_START');
              src.Position += FRAME_HEADER_SIZE - (KEY_SIZE + LENGTH_SIZE);
              
              FrameRecords += 1;
              FrameHeader  := true;
              FrameBody    := false;
            end
          else if KeyCompare(key, FRAME_DATA_START) then
            begin
              LinePrint(offset, FRAME_DATA_START, len, 'FRAME_DATA_START');
              src.Position += FRAME_DATA_SIZE - (KEY_SIZE + LENGTH_SIZE);
              
              FrameRecords += 1;
              FrameBody    := true;
            end
          else if KeyCompare(key, FRAME_FOOTER_START) then
            begin
              LinePrint(offset, FRAME_FOOTER_START, len, 'FRAME_FOOTER_START');
              src.Position += FRAME_FOOTER_SIZE - (KEY_SIZE + LENGTH_SIZE);
              
              FrameRecords += 1;
              if FrameHeader and FrameBody and (src.Position <= src.Length) then
                begin
                  FrameCount += 1;
                  
                  var temp     := src.Position;
                  var length   := FRAME_HEADER_SIZE + FRAME_DATA_SIZE + FRAME_FOOTER_SIZE;
                  var buffer   := new byte[length];
                  src.Position -= length;
                  src.Read(buffer, 0, length);
                  dst.Write(buffer, 0, length);
                  src.Position := temp;
                  
                  Console.WriteLine('frame #{0} copied to dst file!'#13#10, FrameCount);
                end;
            end
          else if KeyCompare(key, FILE_HEADER_START) then
            begin
              LinePrint(offset, FILE_HEADER_START, len, 'FILE_HEADER_START');
              src.Position += FILE_HEADER_SIZE - (KEY_SIZE + LENGTH_SIZE);
            end
          else if KeyCompare(key, FILE_FOOTER_START) then
            begin
              LinePrint(offset, FILE_FOOTER_START, len, 'FILE_FOOTER_START');
              src.Position += FILE_FOOTER_SIZE - (KEY_SIZE + LENGTH_SIZE);
            end
          else
            LinePrint(offset, key, len, 'OTHER');
        end;
    end;
  
  src.Close();
  
  var pos := dst.Position;
  
  AppendFooter(dst, pos, FrameCount);
  AppendHeader(dst, pos, FrameCount);
  
  dst.Close();
  
  var dt := DateTime.Now - t0;
  Console.WriteLine();
  Console.WriteLine('Elapsed time  - '+dt.ToString('hh\:mm\:ss\.fff'));
  
  Console.WriteLine('frame records - {0} ({1:f2} frames)', FrameRecords, FrameRecords/3.0);
  Console.WriteLine('frame count   - {0}', FrameCount);
  
  Console.WriteLine('Done. press any key ... ');
  Console.ReadKey();
end.