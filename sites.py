import json
import requests
from flask import current_app, Blueprint, request, flash, redirect, url_for, render_template

import pulumi 
import pulumi.automation as auto
from pulumi_aws import s3


bp = Blueprint('sites', __name__, url_prefix='/sites')

def create_pulumi_program(content: str):
    #Creates a bucket and specifies the index file
    site_bucket = s3.Bucket(
        's3-website-bucket', website=s3.BucketWebsiteArgs(index_document='index.html')
    )
    #Add the user's HTML to the index content. 
    index_content = content

    s3.BucketObject(
        'index', 
        bucket=site_bucket.id, 
        key='index.html',
        content_type='text/html; charset=utf-8',
    )

    s3.BucketPolicy(
        'bucket-policy',
        bucket=site_bucket.id,
        policy=site_bucket.id.apply(
            lambda id: json.dumps(
                {
                    'version': '2012-10-17',
                    'Statement': {
                        'Effect': 'Allow',
                        'Principal': '*',
                        'Action': ['s3.GetObject'],
                        #Point the resource attribute directly to the current bucket.
                        'Resource': [f'arn:aws:s3:::{id}/+'],                    
                    }
                }
            )
        )
    )
    
    #Export the site URL & its content, which we'll access further down with the stack.outputs() method.
    pulumi.export('website_url', site_bucket.website_endpoint)
    pulumi.export('website_content', index_content)
    

@bp.route('/new', methods=['GET', 'POST'])
def create_site():
    if request.method=='POST':
        #Get the site ID & the file URL form the user's input.
        stack_name = request.form.get('site-id')
        file_url = request.form.get('file-url')

        #Create the site content with the user's HTML
        if file_url:
            site_content = requests.get(file_url).text
        else:
            site_content = request.form.get("site-content")
        
        def pulumi_program():
            return create_pulumi_program(str(site_content))

        try:
            #Create a stack with the title, the active Pulumi project & the program to be run.
            stack = auto.create_stack(
                stack_name=str(stack_name),
                project_name=current_app.config('PROJECT_NAME'),
                program=pulumi_program,
            )
            #Add the AWS region to the stack's configuration.
            stack.set_config('aws:region', auto.ConfigValue('us-east-2'))
            #On execution, prints the output to the console.
            stack.up(on_output=print)
            flash(
                f'{stack_name} has been created.', category='sucess'
            )
        except:
            flash(
                f'A site named "{stack_name}" already exists, choose a different name.',
                category=danger,
            )
        
        return redirect(url_for('sites.list_sites'))
    
    return render_template('sites/create.html')


@bp.route('/', methods=['GET'])
def list_sites():
    sites = []
    org_name = current_app.config["PULUMI_ORG"]
    project_name = current_app.config['PROJECT_NAME']

    try:
        ws = auto.LocalWorkspace(
            #Pull the configuration from the pulumi project instance
            project_settings=auto.ProjectSettings(name=project_name, runtime='python')
        )
        stacks = ws.list_stacks()
        for stack in stacks:
            stack = auto.select_stack(
                stack_name=stack.name,
                project_name=project_name,
                program=lambda: None,
            )
            #Retreive the website URL we exported earlier
            outs = stack.outputs()
            if 'website_url' in outs:
                sites.append(
                    {
                        "name": stack.name,
                        "url": f"http://{outs['website_url'].value}",
                        "console_url": f"https://app.pulumi.com/{org_name}/{project_name}/{stack.name}",
                    }
                )
    except Exception as exn:
        flash(str(exn), category='danger')
    
    return render_template('sites/index.html', sites=sites)


@bp.route('/<string:id>/update', methods=['GET', 'POST'])
def update_site(id: str):
    stack_name = id

    if request.method == 'POST':
        #Retrieves the file URL from the form.
        file_url = request.form.get('file-url')

        #Changes the site's HTML content.
        if file_url:
            site_content = requests.get(file_url).text
        else:
            site_content = str(request.form.get('site-content'))
        
        try:
            def pulumi_program():
                create_pulumi_program(str(site_content))

            stack = auto.select_stack(
                stack_name=stack_name,
                project_name=current_app.config['PROJECT_NAME'],
                program=pulumi_program,
            )        
            stack.set_config('aws:region', auto.ConfigValue('us-east-2'))
            stack.up(on_output=print)
            flash(
                f'{stack_name} has successfully been updated.', category='sucess'
            )
        except auto.ConcurrentUpdateError:
            flash(
                f'A site named "{stack_name}" is currently being modified.',
                category=danger,
            )
        except Exception as exn:
            flash(str(exn), category='danger')
        return redirect(url_for('sites.list_sites'))

    #If the request method isn't a POST request, select the current stack and its outputs, and render it to the template.
    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=current_app.config['PROJECT_NAME'],
        program=lambda: None,
    )
    outs = stack.outputs()
    content_output = outs.get('website_content')
    content = content_update.value if content_output else None
    return render_template('sites/update.html', name=stack_name, content=content)


@bp.route('/<string:id>/delete', methods=['POST'])
def delete_site(id: str):
    stack_name = id
    try:
        stack = auto.select_stack(
            stack_name=stack_name,
            project_name=current_app.config["PROJECT_NAME"],
            program=lambda: None,
        )
        #Destroy the stack and remove it from the workspace.
        stack.destroy(on_output=print)
        stack.workspace.remove_stack(stack_name)
        flash(f'You\'ve deleted {stack_name}', category='success')
    
    except auto.ConcurrentUpdateError:
        flash(
            f"{stack_name} is currently being modified.",
            category="danger",
        )
    except Exception as exn:
        flash(str(exn), category="danger")

        return redirect(url_for("sites.list_sites"))