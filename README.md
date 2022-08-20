#### Staticattic
A minimal hosting platform for static web apps, built using Python, AWS and the pulumi API.

#### Overview
The system was designed to programatically provision infrastructure on AWS, allowing users to create virtual machines (with AWS EC2), given three choices for the instance type.Once the VM is deployed, users are able to upload, or write their static files in-app to be hosted on AWS .

#### Setup
##### AWS
First you'll need to install & configure the AWS cli. Open your terminal and run:
###### Linux
```linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
```
###### Windows
```Windows
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```
###### MacOS
Download the [package file](https://awscli.amazonaws.com/AWSCLIV2.pkg) and follow the on screen instructions to install.

##### Pulumi
Now you should install pulumi:
###### Linux
```Windows
curl -fsSL https://get.pulumi.com | sh
```
###### MacOS
```Windows
brew install pulumi/tap/pulumi
```

###### Windows
[Intall the package](https://www.pulumi.com/docs/get-started/install/) and wollow the on screen instructions to set it up.
#### Configuration
Now run:
```Windows
aws configure
```
You'll be prompted to enter some information regarding your AWS account & prefferences, including your access key, default output format, etc.

Then you'll need to deploy a stack on pulumi by running:
```Windows
pulumi up
```
You'll be prompted to select a stack (if any exists) or to create one.

#### Generating SSH key/value pairs
```Windows
ssh-keygen -m PEM
```
You'll be prompted to enter some info, or you can use the default ones provided.

##### Now you can run the project, open your terminal:
```Windows
flask un
```
