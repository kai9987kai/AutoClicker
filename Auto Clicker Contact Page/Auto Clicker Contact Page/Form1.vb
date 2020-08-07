Public Class Form1
    Private Sub Button1_Click(sender As Object, e As EventArgs) Handles Button1.Click
        Me.Close()
    End Sub

    Private Sub Label3_Click(sender As Object, e As EventArgs) Handles Label3.Click

    End Sub

    Private Sub LinkLabel1_LinkClicked(sender As Object, e As LinkLabelLinkClickedEventArgs) Handles LinkLabel1.LinkClicked
        Process.Start("https://kai9987kai.pw")

    End Sub

    Private Sub ToolTip1_Popup(sender As Object, e As PopupEventArgs) Handles ToolTip1.Popup
        Dim buttonToolTip As New ToolTip()

        buttonToolTip.ToolTipTitle = "Button Tooltip"

        buttonToolTip.UseFading = True

        buttonToolTip.UseAnimation = True

        buttonToolTip.IsBalloon = True

        buttonToolTip.ShowAlways = True

        buttonToolTip.AutoPopDelay = 5000

        buttonToolTip.InitialDelay = 1000

        buttonToolTip.ReshowDelay = 500

        buttonToolTip.IsBalloon = True

        buttonToolTip.SetToolTip(Button1, "Click me to execute.")
    End Sub

    Private Sub Label5_Click(sender As Object, e As EventArgs) Handles Label5.Click

    End Sub

    Private Sub Label1_Click(sender As Object, e As EventArgs) Handles Label1.Click

    End Sub
End Class
