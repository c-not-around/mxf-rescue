{$apptype windows}
{$mainresource res\scan.res}


uses
  System,
  System.Diagnostics;


begin
  var cd      := Environment.CurrentDirectory;
  var pythonw := '"' + cd + '\Python38\python.exe"';
  var idle    := '"' + cd + '\scan.py"';
  
  var StartInfo := new ProcessStartInfo(pythonw, idle);
  StartInfo.Verb := 'runas';
  var process := Process.Start(StartInfo);
  while not process.HasExited do ;
end.