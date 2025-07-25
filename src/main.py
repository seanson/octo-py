import re

import click
from tabulate import tabulate
from tqdm import tqdm

from octopus import OctopusClient


@click.group()
@click.pass_context
def cli(ctx):
    """Octopus Deploy CLI tool"""
    ctx.ensure_object(dict)
    try:
        ctx.obj["client"] = OctopusClient()
    except Exception as e:
        click.echo(f"Error initializing Octopus client: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.pass_context
def spaces(ctx):
    """List all spaces"""
    client = ctx.obj["client"]
    try:
        spaces_list = client.get_spaces()
        for space in spaces_list:
            click.echo(f"{space['Id']}: {space['Name']}")
    except Exception as e:
        click.echo(f"Error fetching spaces: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("space_id")
@click.pass_context
def projects(ctx, space_id):
    """List projects in a space"""
    client = ctx.obj["client"]
    try:
        projects_list = client.get_projects(space_id)
        for project in projects_list:
            click.echo(f"{project['Id']}: {project['Name']}")
    except Exception as e:
        click.echo(f"Error fetching projects: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("space_id")
@click.argument("project_id")
@click.pass_context
def releases(ctx, space_id, project_id):
    """List releases for a project in a space"""
    client = ctx.obj["client"]
    try:
        releases_list = client.get_releases(space_id, project_id)
        for release in releases_list:
            click.echo(f"{release['Id']}: {release['Version']}")
    except Exception as e:
        click.echo(f"Error fetching releases: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("space_id")
@click.argument("project_id")
@click.option("--environment", default="staging", help="Environment name (default: staging)")
@click.pass_context
def latest_release(ctx, space_id, project_id, environment):
    """Get the latest release deployed to an environment"""
    client = ctx.obj["client"]
    try:
        release = client.get_latest_release_in_environment(space_id, project_id, environment)
        if release:
            click.echo(f"{release['Id']}: {release['Version']}")
        else:
            click.echo(f"No releases found in {environment} environment")
    except Exception as e:
        click.echo(f"Error fetching latest release: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("space_name")
@click.argument("project_name")
@click.pass_context
def promote(ctx, space_name, project_name):
    """Promote the latest staging release to QA"""
    client = ctx.obj["client"]
    try:
        # Find the space by name
        space = client.get_space_by_name(space_name)
        if not space:
            click.echo(f"Space '{space_name}' not found")
            ctx.exit(1)

        # Find the project by name
        project = client.get_project_by_name(space["Id"], project_name)
        if not project:
            click.echo(f"Project '{project_name}' not found in space '{space_name}'")
            ctx.exit(1)

        # Get the latest release from staging
        staging_release = client.get_latest_release_in_environment(
            space["Id"], project["Id"], "staging"
        )
        if not staging_release:
            click.echo("No releases found in staging environment")
            ctx.exit(1)

        # Find the QA environment
        environments = client.get_environments(space["Id"])
        qa_env = None
        for env in environments:
            if env.get("Name", "").lower() == "qa":
                qa_env = env
                break

        if not qa_env:
            click.echo("QA environment not found")
            ctx.exit(1)

        # Deploy the staging release to QA
        click.echo(f"Promoting release {staging_release['Version']} from staging to QA...")
        deployment = client.deploy_release(space["Id"], staging_release["Id"], qa_env["Id"])
        click.echo(f"Deployment created: {deployment['Id']}")

    except Exception as e:
        click.echo(f"Error promoting release: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("source_environment")
@click.argument("target_environment")
@click.option("--space", required=True, help="Space name")
@click.option("--filter", help="Filter projects by name (case-insensitive substring match)")
@click.option(
    "--exclude", multiple=True, help="Exclude projects by name (case-insensitive substring match)"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be deployed without actually deploying"
)
@click.option(
    "--tabulate-format",
    default="grid",
    help="Table format for output (e.g., grid, simple, plain, pipe, html)",
)
@click.option(
    "--tabulate-output", help="Filename to write tabulate output to instead of printing to console"
)
@click.pass_context
def deploy_all(
    ctx,
    source_environment,
    target_environment,
    space,
    filter,
    exclude,
    dry_run,
    tabulate_format,
    tabulate_output,
):
    """Deploy latest releases from source environment to target environment for all projects in a space"""
    client = ctx.obj["client"]
    try:
        # Find the space by name
        space_obj = client.get_space_by_name(space)
        if not space_obj:
            click.echo(f"Space '{space}' not found")
            ctx.exit(1)

        # Get all projects in the space
        all_projects = client.get_projects(space_obj["Id"])

        # Apply filtering and exclusion
        projects = all_projects

        # Apply filter if provided
        if filter:
            projects = [p for p in projects if filter.lower() in p.get("Name", "").lower()]

        # Apply exclusion if provided
        if exclude:
            for exclude_pattern in exclude:
                projects = [
                    p for p in projects if exclude_pattern.lower() not in p.get("Name", "").lower()
                ]

        # Report filtering results
        if filter and exclude:
            exclude_list = "', '".join(exclude)
            click.echo(
                f"Found {len(projects)} projects matching filter '{filter}' and excluding '{exclude_list}'"
            )
        elif filter:
            click.echo(f"Found {len(projects)} projects matching filter '{filter}'")
        elif exclude:
            exclude_list = "', '".join(exclude)
            click.echo(f"Found {len(projects)} projects excluding '{exclude_list}'")
        else:
            click.echo(f"Found {len(projects)} projects in space '{space}'")

        # Find the target environment
        environments = client.get_environments(space_obj["Id"])
        target_env = None
        for env in environments:
            if env.get("Name", "").lower() == target_environment.lower():
                target_env = env
                break

        if not target_env:
            click.echo(f"Target environment '{target_environment}' not found")
            ctx.exit(1)

        results = []

        with tqdm(projects, desc="Processing projects", unit="project") as pbar:
            for project in pbar:
                project_name = project.get("Name", "")
                pbar.set_description(f"Processing {project_name}")

                # Get the latest release from source environment
                source_release = client.get_latest_release_in_environment(
                    space_obj["Id"], project["Id"], source_environment
                )

                if not source_release:
                    result_entry = {
                        "Project": project_name,
                        f"{source_environment.title()} Version": "N/A",
                        f"{target_environment.title()} Version": "N/A",
                        "Action": "Skipped",
                    }
                    result_entry["Changelog"] = "_No source release found_"
                    results.append(result_entry)
                    continue

                source_version = source_release["Version"]

                # Get the latest release from target environment
                target_release = client.get_latest_release_in_environment(
                    space_obj["Id"], project["Id"], target_environment
                )

                target_version = target_release["Version"] if target_release else "N/A"

                # Check if versions match
                if target_release and source_version == target_version:
                    result_entry = {
                        "Project": project_name,
                        f"{source_environment.title()} Version": source_version,
                        f"{target_environment.title()} Version": target_version,
                        "Action": "Already deployed",
                    }
                    result_entry["Changelog"] = "_Already deployed - no changes_"
                    results.append(result_entry)
                    continue

                if dry_run:
                    # Get changelog for version differences
                    changelog = ""
                    if target_version != "N/A":
                        changelog = client.get_changelog_between_versions(
                            space_obj["Id"], project["Id"], target_version, source_version
                        )
                    else:
                        # No target version, get release notes for just the source version
                        source_details = client.get_release_details(
                            space_obj["Id"], source_release["Id"]
                        )
                        if source_details and source_details.get("ReleaseNotes"):
                            changelog = f"**{source_version}**\n{source_details['ReleaseNotes']}"
                        else:
                            changelog = f"**{source_version}**\n_No release notes available_"

                    result_entry = {
                        "Project": project_name,
                        f"{source_environment.title()} Version": source_version,
                        f"{target_environment.title()} Version": target_version,
                        "Action": "Would deploy",
                    }

                    # Add changelog to the table in dry-run mode
                    if changelog:
                        # Only replace newlines with spaces to prevent table breaking
                        replace_newline = "<br>" if tabulate_format in ["github"] else " "
                        sanitized_changelog = re.sub(r"\n+", replace_newline, changelog)
                        result_entry["Changelog"] = sanitized_changelog
                    else:
                        result_entry["Changelog"] = "_No changelog available_"

                    results.append(result_entry)
                else:
                    try:
                        client.deploy_release(
                            space_obj["Id"], source_release["Id"], target_env["Id"]
                        )
                        result_entry = {
                            "Project": project_name,
                            f"{source_environment.title()} Version": source_version,
                            f"{target_environment.title()} Version": source_version,
                            "Action": "Deployed",
                        }
                        # No changelog for actual deployments
                        results.append(result_entry)
                    except Exception as e:
                        result_entry = {
                            "Project": project_name,
                            f"{source_environment.title()} Version": source_version,
                            f"{target_environment.title()} Version": target_version,
                            "Action": f"Failed: {e!s}",
                        }
                        # No changelog for failed deployments
                        results.append(result_entry)

        # Print results table
        if results:
            # Filter out skipped items from the table display and sort alphabetically by project name
            filtered_columns = ["Action"]
            filtered_results = [
                {k: v for k, v in r.items() if k not in filtered_columns}
                for r in results
                if r["Action"] != "Skipped"
            ]
            filtered_results.sort(key=lambda x: x["Project"].lower())

            if filtered_results:
                table_output = tabulate(filtered_results, headers="keys", tablefmt=tabulate_format)

                if tabulate_output:
                    # Write to file
                    with open(tabulate_output, "w") as f:
                        f.write(table_output)
                    click.echo(f"\nTable output written to: {tabulate_output}")
                else:
                    # Print to console
                    click.echo("\n" + table_output)

            # Summary statistics
            deployed_count = len([r for r in results if r["Action"] == "Deployed"])
            would_deploy_count = len([r for r in results if r["Action"] == "Would deploy"])
            failed_count = len([r for r in results if "failed" in r["Action"].lower()])
            already_deployed_count = len([r for r in results if r["Action"] == "Already deployed"])
            skipped_count = len([r for r in results if r["Action"] == "Skipped"])

            if dry_run:
                click.echo(
                    f"\n📊 Summary: {would_deploy_count} would be deployed, {already_deployed_count} already deployed, {skipped_count} skipped, {failed_count} failed"
                )
            else:
                click.echo(
                    f"\n📊 Summary: {deployed_count} deployed, {already_deployed_count} already deployed, {skipped_count} skipped, {failed_count} failed"
                )
        else:
            click.echo("No projects to process")

    except Exception as e:
        click.echo(f"Error in bulk promotion: {e}", err=True)
        raise
        ctx.exit(1)


if __name__ == "__main__":
    cli()
