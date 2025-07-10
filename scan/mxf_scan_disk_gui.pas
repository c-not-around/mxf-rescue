{$apptype windows}
{$mainresource res\scan.res}


uses
  System,
  System.Diagnostics;

  
begin
  var cd      := Environment.CurrentDirectory;
  var pythonw := '"' + cd + '\Python38\pythonw.exe"';
  var idle    := '"' + cd + '\scan.pyw"';
  
  var StartInfo := new ProcessStartInfo(pythonw, idle);
  StartInfo.WindowStyle := ProcessWindowStyle.Hidden;
  var process := Process.Start(StartInfo);
  while not process.HasExited do ;
end.