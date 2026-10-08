using System;
using System.Windows.Forms;

namespace Acme.Client.Forms
{
    // 受注入力画面
    public partial class OrderFrm : Form
    {
        public OrderFrm()
        {
            InitializeComponent();
        }

        // 保存ボタン押下時
        private void btnSave_Click(object sender, EventArgs e)
        {
            // 納期チェック
            if (dtpDeliveryDate.Value < dtpOrderDate.Value)
            {
                MessageBox.Show("納期は受注日以降を指定してください。");
                dtpDeliveryDate.Focus();
                return;
            }
            SaveOrder();
        }

        private void SaveOrder()
        {
            var svc = new OrderServiceClient();
            svc.Save(txtOrderId.Text, dtpOrderDate.Value, dtpDeliveryDate.Value);
        }
    }
}
