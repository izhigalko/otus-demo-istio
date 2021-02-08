import platform

from aiohttp import web, client, ClientResponseError

routes = web.RouteTableDef()
memoized_times = None


@routes.get('/')
async def hello(request: web.Request):
    url = request.query.get('url', '')

    headers = '\n'.join(f'{k}: {v}' for k, v in request.headers.items())

    text = f'Request served by {platform.node()}\n\n'
    text += f'{request.version} {request.method} {request.url}\n\n'
    text += f'Request headers:\n\n{headers}\n\n'

    if url:
        s: client.ClientSession
        r: client.ClientResponse

        async with client.ClientSession(raise_for_status=True) as s:
            data = None
            if request.can_read_body:
                data = await request.text()

            ext_req_headers = {}
            token = request.headers.get('X-AUTH-TOKEN')
            if token:
                ext_req_headers['X-AUTH-TOKEN'] = token

            try:
                async with s.request(request.method, url, headers=ext_req_headers, data=data) as r:
                    body = await r.text()
                    headers = '\n'.join(f'{k}: {v}' for k, v in r.headers.items())
                    text += f'Remote status: {r.status}\n\nRemote headers:\n\n{headers}\n\nRemote body:\n\n{body}'
            except ClientResponseError as e:
                headers = '\n'.join(f'{k}: {v}' for k, v in e.headers.items())
                text += f'Remote error with status: {e.status}\n\nRemote headers: {headers}'
            except Exception as e:
                text += f'Remote error: {str(e)}'

    return web.Response(content_type='text/plain', text=text)


@routes.get('/error')
async def timeout(request: web.Request):
    global memoized_times
    times = int(request.query.get('times', '') or 0)

    if memoized_times is None:
        memoized_times = times + 1

    memoized_times -= 1
    status = 500

    if memoized_times <= 0:
        memoized_times = None
        status = 200

    return web.Response(content_type='text/plain', status=status)

if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8080)
