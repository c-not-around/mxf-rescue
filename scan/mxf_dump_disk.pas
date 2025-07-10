{$apptype windows}
{$mainresource res\scan.res}


uses
  System,
  System.Diagnostics,
  System.Threading;

  
begin
  var cd      := Environment.CurrentDirectory;
  var pythonw := '"' + cd + '\Python38\pythonw.exe"';
  var idle    := '"' + cd + '\dump.pyw"';
  
  var StartInfo := new ProcessStartInfo(pythonw, idle);
  StartInfo.Verb := 'runas';
  var process := Process.Start(StartInfo);
  while not process.HasExited do
    Thread.Sleep(500);
end.