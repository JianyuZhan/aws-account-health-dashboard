import aws_cdk as cdk
from cdk_infra.infra_stack import AwsHealthDashboard

app = cdk.App()
AwsHealthDashboard(app, "AwsHealthDashboardStack")
app.synth()

