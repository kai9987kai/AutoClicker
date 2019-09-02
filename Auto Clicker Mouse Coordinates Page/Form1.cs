// Decompiled with JetBrains decompiler
// Type: WindowsFormsApplication4.Form1
// Assembly: WindowsFormsApplication4, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null
// MVID: 92B05EC8-D565-495B-8123-95A419BC3CBE
// Assembly location: C:\Users\test\Documents\GitHub\AutoClicker\MousePos.exe

using System;
using System.ComponentModel;
using System.Drawing;
using System.Windows.Forms;

namespace AutoClickerMouseCoordinatesPage
{
  public class Form1 : Form
  {
    private IContainer components;
    private Label label1;
    private Timer timer1;

    protected override void Dispose(bool disposing)
    {
      if (disposing && this.components != null)
        this.components.Dispose();
      base.Dispose(disposing);
    }

    private void InitializeComponent()
    {
      this.components = (IContainer) new Container();
      this.label1 = new Label();
      this.timer1 = new Timer(this.components);
      this.SuspendLayout();
      this.label1.AutoSize = true;
      this.label1.Location = new Point(12, 9);
      this.label1.Name = "label1";
      this.label1.Size = new Size(35, 13);
      this.label1.TabIndex = 0;
      this.label1.Text = "label1";
      this.timer1.Enabled = true;
      this.timer1.Interval = 10;
      this.timer1.Tick += new EventHandler(this.timer1_Tick);
      this.AutoScaleDimensions = new SizeF(6f, 13f);
      this.AutoScaleMode = AutoScaleMode.Font;
      this.ClientSize = new Size(90, 29);
      this.Controls.Add((Control) this.label1);
      this.FormBorderStyle = FormBorderStyle.FixedToolWindow;
      this.Name = nameof (Form1);
      this.Text = "Mouse Coordinates";
      this.TopMost = true;
      this.ResumeLayout(false);
            this.ShowInTaskbar = false;
      this.PerformLayout();
    }

    public Form1()
    {
      this.InitializeComponent();
    }

    private void timer1_Tick(object sender, EventArgs e)
    {
      this.label1.Text = "X:" + Cursor.Position.X.ToString() + " " + "Y:" + Cursor.Position.Y.ToString();
    }
  }
}
