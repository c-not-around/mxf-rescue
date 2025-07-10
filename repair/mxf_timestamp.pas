uses
  System,
  System.Text.RegularExpressions,
  System.IO;


type
  TKey = array of byte;


const
  KEY_SIZE          = 16;
  LENGTH_SIZE       = 4;
  
  FILE_HEADER_SIZE  = 11264;
  FILE_FOOTER_SIZE  = 10800;
  
  FRAME_HEADER_SIZE = 512;
  FRAME_DATA_SIZE   = 7452672;
  FRAME_FOOTER_SIZE = 36352;
  
  FILE_HEADER_START : TKey = ($02, $05, $01, $01, $0D, $01, $02, $01, $01, $02, $04, $00);
  FILE_FOOTER_START : TKey = ($02, $05, $01, $01, $0D, $01, $02, $01, $01, $04, $04, $00);
  
  FRAME_HEADER_START: TKey = ($02, $05, $01, $01, $0D, $01, $03, $01, $04, $01, $01, $00);
  FRAME_DATA_START  : TKey = ($01, $02, $01, $06, $0E, $06, $0D, $03, $19, $01, $45, $00);
  FRAME_FOOTER_START: TKey = ($01, $02, $01, $01, $0D, $01, $03, $01, $16, $04, $03, $00);


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

procedure LinePrint(adr: longword; key: array of byte; len: longword; desc: string);
begin
  Console.Write('{0:X8}: ', adr);
  Console.Write('060E2B34');
  for var i := 0 to 11 do
    Console.Write('{0:X2}', key[i]);
  Console.WriteLine(' {0:X8} - {1:s}', len, desc);
end;

function GetTimeStamp(fs: FileStream; offset: int64): longword;
begin
  fs.Position := offset;
  result := 0;
  for var i := 0 to 3 do
    result := (result shl 8) or fs.ReadByte();
end;

procedure SetTimeStamp(fs: FileStream; offset: int64; ts: longword);
begin
  var data := new byte[4];
  for var i := 3 downto 0 do
    begin
      data[i] := ts;
      ts := ts shr 8;
    end;
  
  fs.Position := offset;
  fs.Write(data, 0, 4);
end;

function TimeStampDecode(ts: longword): string;
begin
  var f := ts mod 25;
  ts := ts div 25;
  
  var s := ts mod 60;
  ts := ts div 60;
  
  var m := ts mod 60;
  ts := ts div 60;
  
  var h := ts mod 60;
  ts := ts div 60;
  
  result := String.Format('{0:d2}:{1:d2}:{2:d2}.{3:d2}', h, m, s, f);
end;

function TimeStampEncode(ts: string): longword;
begin
  var parts := ts.Split(':', '.');
  
  var h := Convert.ToInt32(parts[0]);
  var m := Convert.ToInt32(parts[1]);
  var s := Convert.ToInt32(parts[2]);
  var f := Convert.ToInt32(parts[3]);
  
  result := f + 25 * (s + 60 * (m + 60 * h));
end;

begin
  var fname := ''; //'01702__rebuilt.mxf';
  
  while not &File.Exists(fname) do
    begin
      Console.Write('file: ');
      fname := Console.ReadLine();
    end;
  
  var data := &File.OpenRead(fname);
  
  var ts1 := GetTimeStamp(data, $0C1B);
  var ts2 := GetTimeStamp(data, $15E6);
  Console.WriteLine('Header timestamp1: {0:X8} - {1}', ts1, TimeStampDecode(ts1));
  Console.WriteLine('Header timestamp2: {0:X8} - {1}', ts2, TimeStampDecode(ts2));
  
  var flag := true;
  data.Position := data.Length - FILE_FOOTER_SIZE;
  if FindAtomKey(data) and KeyCompare(GetKey(data), FILE_FOOTER_START) then
    begin
      var offset := data.Position - KEY_SIZE;
      ts1 := GetTimeStamp(data, offset + $0C1B);
      ts2 := GetTimeStamp(data, offset + $15E6);
      Console.WriteLine('Footer timestamp1: {0:X8} - {1}', ts1, TimeStampDecode(ts1));
      Console.WriteLine('Footer timestamp2: {0:X8} - {1}', ts2, TimeStampDecode(ts2));
    end
  else
    begin
      flag := false;
      Console.WriteLine('footer is missing!');
    end;
  
  data.Close();
  
  var image := '';
  while not Regex.IsMatch(image, '^\d{1,2}\:\d{1,2}\:\d{1,2}\.\d{1,2}$') do
    begin
      Console.Write('desired timestamp (format hh:mm:ss.ff): ');
      image := Console.ReadLine();
    end;
  
  ts1 := TimeStampEncode(image);
  
  data := &File.OpenWrite(fname);
  
  SetTimeStamp(data, $0C1B, ts1);
  SetTimeStamp(data, $15E6, ts1);
  if flag then
    begin
      var offset := data.Length - FILE_FOOTER_SIZE;
      SetTimeStamp(data, offset+$0C1B, ts1);
      SetTimeStamp(data, offset+$15E6, ts1);
    end;
  
  data.Close();
  
  Console.WriteLine('Done. press any key ... ');
  Console.ReadKey();
end.