// Decompiled with JetBrains decompiler
// Type: WindowsFormsApplication4.Program
// Assembly: WindowsFormsApplication4, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null
// MVID: 92B05EC8-D565-495B-8123-95A419BC3CBE
// Assembly location: C:\Users\test\Documents\GitHub\AutoClicker\MousePos.exe

using System;
using System.Windows.Forms;

namespace AutoClickerMouseCoordinatesPage
{
  internal static class Program
  {
    [STAThread]
    private static void Main()
    {
      Application.EnableVisualStyles();
      Application.SetCompatibleTextRenderingDefault(false);
      Application.Run((Form) new Form1());
    }
  }
}
