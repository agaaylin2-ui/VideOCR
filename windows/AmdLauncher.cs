using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("VideOCR AMD Preview")]
[assembly: AssemblyProduct("VideOCR AMD Preview")]
[assembly: AssemblyVersion("0.1.0.0")]

internal static class AmdLauncher
{
    // -File passes the selected script and paths as data to Windows PowerShell.
    // Paths are absolute filenames, so none can end in a directory separator.
    private static string QuoteFile(string path)
    {
        return "\"" + Path.GetFullPath(path) + "\"";
    }

    [STAThread]
    private static int Main(string[] args)
    {
        bool interactive = args.Length == 0;
        try
        {
            string folder = AppDomain.CurrentDomain.BaseDirectory;
            string script = "run-amd-video.ps1";
            string files = "";
            if (interactive)
            {
                Console.Title = "VideOCR AMD Preview";
                Console.WriteLine("VideOCR AMD Preview | Windows 11 | Radeon RX 9070 XT");
                Console.WriteLine("Press Enter to export subtitles from a video.");
                Console.WriteLine("On a new PC, install Python 3.12 x64 and 7-Zip, then run options 1 and 2 in order.");
                Console.WriteLine("1  Prepare models and DirectML");
                Console.WriteLine("2  Check a subtitle screenshot and prepare OCR");
                string choice = Console.ReadLine();
                switch (choice)
                {
                    case "": break;
                    case "1": script = "run-amd-test.ps1"; break;
                    case "2": script = "run-real-ocr-test.ps1"; break;
                    default: throw new ArgumentException("Choose 1, 2 or Enter when you reopen the launcher.");
                }
            }
            else if (args.Length == 3 && args[0] == "--export")
            {
                files = " -Video " + QuoteFile(args[1]) + " -OutputFile " + QuoteFile(args[2]);
            }
            else
            {
                throw new ArgumentException("Usage: VideOCR-AMD.exe [--export video_file new_subtitle.srt]");
            }
            string helper = Path.Combine(folder, script);
            if (!File.Exists(helper))
                throw new FileNotFoundException("Extract the entire VideOCR ZIP and keep the EXE beside " + script + ".");
            string powershell = Path.Combine(Environment.SystemDirectory, @"WindowsPowerShell\v1.0\powershell.exe");
            var start = new ProcessStartInfo(powershell,
                "-NoProfile -ExecutionPolicy Bypass -File " + QuoteFile(helper) + files);
            start.UseShellExecute = false;
            start.WorkingDirectory = folder;
            using (var child = Process.Start(start))
            {
                child.WaitForExit();
                if (interactive && (child.ExitCode != 0 || script != "run-amd-video.ps1"))
                    MessageBox.Show("Read the result in the console window. Click OK when you are finished.", "VideOCR AMD Preview");
                return child.ExitCode;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            if (interactive) MessageBox.Show(ex.Message, "VideOCR AMD Preview");
            return 1;
        }
    }
}
