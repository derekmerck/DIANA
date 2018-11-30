import click
from diana.daemon import DianaWatcher
from diana.daemon.watcher import set_proxied_index_route, set_upload_files_route,\
                                 set_anon_and_forward_route, set_index_tags_route, \
                                 set_index_instance_tags_route
from utils.merge_yaml_sources import merge_yaml_sources

@click.command()
@click.option('-r', '--routes',
              help='Routing description (DIANA_ROUTES)')
@click.option('-R', '--routes_path',
              help='Path to routes file or directory (DIANA_ROUTES_PATH)',
              type = click.Path(exists=True))
@click.pass_context
def watch(ctx, routes, routes_path):
    """Monitor sources and ROUTE dixels to destinations"""
    services = ctx.obj['SERVICES']
    click.echo(watch.__doc__)

    # Read routes
    all_routes = merge_yaml_sources(routes, routes_path)

    def get_route(handler, source, dest):
        # Named DIANA routes

        source_kwargs = services.get(source)
        dest_kwargs = services.get(dest)

        if handler == "proxied_index":
            route = set_proxied_index_route(source_kwargs, dest_kwargs)
        elif handler == "upload_file":
            route = set_upload_files_route(source_kwargs, dest_kwargs)
        elif handler == "anon_and_forward":
            route = set_anon_and_forward_route(source_kwargs, dest_kwargs)
        elif handler == "index_tags":
            route = set_index_tags_route(source_kwargs, dest_kwargs)
        elif handler == "index_instance_tags":
            route = set_index_instance_tags_route(source_kwargs, dest_kwargs)
        else:
            raise ValueError('No loader for route type "{}"'.format(handler))

        return route

    # Expand route definitions into object-specific routes
    expanded_routes = {}
    for route_def in all_routes:
        expanded_route = get_route(**route_def)
        expanded_routes.update( expanded_route )

    watcher = DianaWatcher()
    watcher.add_routes(expanded_routes)
    watcher.run()
