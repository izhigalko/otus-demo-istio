from aiohttp import web, client

routes = web.RouteTableDef()


@routes.get('/')
async def hello(request: web.Request):
    url = request.query.get('url', '')

    headers = '\n'.join(f'{k}: {v}' for k, v in request.headers.items())
    text = f'Request headers:\n\n{headers}\n\n'

    if url:
        s: client.ClientSession
        r: client.ClientResponse

        async with client.ClientSession(raise_for_status=True) as s:
            data = None
            if request.can_read_body:
                data = await request.text()

            async with s.request(request.method, url, data=data) as r:
                body = await r.text()
                headers = '\n'.join(f'{k}: {v}' for k, v in r.headers.items())
                text += f'Remote headers:\n\n{headers}\n\nRemote body:\n\n{body}'

    return web.Response(content_type='text/plain', text=text)

if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8080)
