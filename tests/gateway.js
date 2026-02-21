function unwrap(r) {
    r.subrequest('/proxy' + r.uri, { method: r.method }, function(reply) {

        if (reply.status !== 200) {
            r.return(502, "Lambda Bridge Error: " + reply.status);
            return;
        }

        // Check for empty/undefined body
        if (!reply.responseBody) {
            ngx.log(ngx.ERR, "CRITICAL: Lambda returned 200 but body is EMPTY/UNDEFINED");
            r.return(502, "Lambda returned empty response. Check Python logs for logic errors.");
            return;
        }

        try {
            var response = JSON.parse(reply.responseBody);
            r.return(response.statusCode || 200, response.body || "");
        } catch (e) {
            ngx.log(ngx.ERR, "JSON Parse Error: " + e.message + " | Body: " + reply.responseBody);
            r.return(502, "Invalid JSON from Lambda");
        }
    });
}
export default { unwrap };
