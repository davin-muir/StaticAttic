from flask import Blueprint, current_app, request, flash, redirect, url_for, render_template
from pathlib import Path

import pulumi.automation as auto
import pulumi_aws as aws
import pulumi 
import os 



bp = Blueprint('virtual_machines', __name__, url_prefix='/vms')
instance_types = ['t2.micro', 't3.micro', "c5.xlarge", "p2.xlarge"]



def create_pulumi_program(keydata: str, instance_type=str):
    ami = aws.ec2.get_ami(
        most_recent=True,
        owners=['amazon'],
        filters=[aws.GetAmiFilterArgs(name='name', values=["*amzn2-ami-minimal-hvm*"])]
    )

    group = aws.ec2.SecurityGroup(
        'web-secgrp',
        description='Enable SSH access',
        ingress=[aws.ec2.SecurityGroupIngressArgs(
            protocol='tcp',
            from_port=22,
            to_port=22,
            #CIDR blocks specify the range of IPv4 addresses for the VM.
            cidr_blocks=['0.0.0.0/0'],
        )]
    )

    public_key = keydata

    if public_key is None or public_key == '':
        #Pull the public key from the local environment
        home = str(Path.home())
        f = open(os.path.join(home, '.ssh/id_rsa.pub'), 'r')
        public_key = f.read()
        f.close()

    public_key = public_key.strip()  
    print(f'Public Key: "{public_key}"\n') 


    keypair = aws.ec2.KeyPair('dlami-keypair', public_key=public_key)

    server = aws.ec2.Instance(
        'dlami-server',
        instance_type=instance_type,
        vpc_security_group_ids=[group.id],
        key_name=keypair.id,
        ami=ami.id
    )

    pulumi.export('instance_type', server.instance_type)
    pulumi.export('public_key', keypair.public_key)
    pulumi.export('public_ip', server.public_ip)
    pulumi.export('public_dns', server.public_dns)



@bp.route('/new', methods=['GET', 'POST'])
def create_vm():
    if request.method == 'POST':
        stack_name = request.form.get('vm-id')
        keydata = request.form.get('vm-keypair')
        instance_type = request.form.get('instance_type')
        
        #Create a VM with the user's choices.
        def pulumi_program():
            return create_pulumi_program(keydata, instance_type)
        try:
            stack = auto.create_stack(
                stack_name=str(stack_name),
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program,
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))
            
            stack.up(on_output=print)
            flash(
                f"Successfully created VM: '{stack_name}'", category="success")

        except auto.StackAlreadyExistsError:
            flash(
                f"Error: A VM called '{stack_name}' already exists, choose a different name.",
                category="danger",
            )
        return redirect(url_for("virtual_machines.list_vms"))
    
    current_app.logger.info(f'Instance types: {instance_types}')
    return render_template('virtual_machines/create.html', instance_types=instance_types, curr_instance_type=None)



@bp.route("/", methods=["GET"])
def list_vms():
    vms = []
    org_name = current_app.config["PULUMI_ORG"]
    project_name = current_app.config["PROJECT_NAME"]

    try:
        ws = auto.LocalWorkspace(
            project_settings=auto.ProjectSettings(
                name=project_name, runtime="python")
        )
        
        #Retrieve all active stacks in the workspace
        stacks = ws.list_stacks()
        for stack in stacks:
            stack = auto.select_stack(
                stack_name=stack.name,
                project_name=project_name,
                program=lambda: None,
            )
            outs = stack.outputs()
            if 'public_dns' in outs:
                vms.append(
                    {
                        "name": stack.name,
                        "dns_name": f"{outs['public_dns'].value}",
                        "console_url": f"https://app.pulumi.com/{org_name}/{project_name}/{stack.name}",
                    }
                )

    except Exception as exn:
        flash(str(exn), category="danger")

    current_app.logger.info(f"VMS: {vms}")
    return render_template("virtual_machines/index.html", vms=vms)



@bp.route('/<string:id>/update', methods=['GET', 'POST'])
def update_vm(id: str):
    stack_name = id
    if request.method == 'POST':
        current_app.logger.ingo(
            f'Updating VM: {stack_name}, form data: {request.form}'
        )

        keydata = request.form.get('vm-keypair')
        current_app.logger.info(f'Updating keydata: {keydata}')
        instance_type = request.form.get('instance_type')

        def pulumi_program():
            return create_pulumi_program(keydata, instance_type)

        try:
            stack = auto.select_stack(
                stack_name=stack.name,
                project_name=current_app.config['PROJECT_NAME'],
                program=pulumi_program,
            )
            stack.set_config('aws:region', auto.ConfigValue('us-east-1'))
            stack.up(on_output=print)
            flash(f'You\'ve successfully updated the VM: "{stack_name}."', category="success")
        
        except auto.ConcurrentUpdateError:
            flash(
                f'{stack_name} is currently being modified.', category='danger'
            )
        
        except Exception as exn:
            flash(
                str(exn), category='danger'
            )

    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=current_app.config['PROJECT_NAME'],
        program=lambda: None,
    )
    outs = stack.outputs()
    public_key = outs.get('public_key')
    pk = public_key.value if public_key else None 
    instance_type = outs.get('instance_type')
    return render_template('virtual_machines/update.html', name=stack_name, public_key=pk, instance_types=instance_types, curr_instance_type=instance_type.value)




@bp.route('/<string:id>/delete', methods=['POST'])
def delete_vm(id: str):
    stack_name = id
    try:
        stack = auto.select_stack(
            stack_name=stack_name,
            project_name=current_app.config['PROJECT_NAME'],
            program=lambda: None,
        )
        stack.destroy(on_output=print)
        stack.workspace.remove_stack(stack_name)
        flash(f"You've successfully deleted the VM: '{stack_name}'.", category="success")

    except auto.ConcurrentUpdateError:
        flash(
            f"{stack_name} is currently being modified.",
            category="danger",
        )

    except Exception as exn:
        flash(str(exn), category="danger")

    return redirect(url_for("virtual_machines.list_vms"))