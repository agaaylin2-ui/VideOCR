using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("VideOCR AMD Desktop")]
[assembly: AssemblyProduct("VideOCR AMD Desktop")]
internal static class DesktopLauncher
{
    [STAThread]
    private static int Main()
    {
        try
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string python = Path.Combine(root, "runtime", "pythonw.exe");
            string bootstrap = Path.Combine(root, "app", "desktop.pyw");
            if (!File.Exists(python) || !File.Exists(bootstrap))
                throw new FileNotFoundException("Extract the entire AMD Desktop ZIP before opening VideOCR-AMD.exe.");
            var start = new ProcessStartInfo(python, "-E -s -X utf8 \"" + bootstrap + "\"");
            start.WorkingDirectory = Path.GetDirectoryName(bootstrap);
            start.UseShellExecute = false;
            using (var gui = Process.Start(start))
            {
                gui.WaitForExit();
                return gui.ExitCode;
            }
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "VideOCR AMD Desktop");
            return 1;
        }
    }
}
