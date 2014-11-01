<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>Libsendungsverfolgung Spielwiese</title>
        <script type="text/javascript" src="https://code.jquery.com/jquery-2.1.1.min.js"></script>
        <script type="text/javascript">
function gls_json_weight(data) {
    if(data.status == "success") {
        var duplicate = false;
        $("#weights tr > td:nth-child(2)").each(function(i, td) {
            if($(td).text() == data.barcode) {
                duplicate = true;
            }
        });
        if(!duplicate) {
            $("#weights").append("<tr><td>abc</td><td></td><td></td><td></td><td></td></tr>")
            var row = $("#weights tr:last");
            row.children("td:nth-child(1)").text(data.date);
            row.children("td:nth-child(2)").text(data.barcode);
            row.children("td:nth-child(5)").text(data.weight);
        } else {
            $("#errors").append("<li>Paket-Nr. " + data.barcode + " bereits vorhanden</li>");
        }
    } else {
        $("#errors").append("<li>Paket-Nr. " + data.barcode + " ungültig/noch nicht gescannt</li>");
    }

    if($("#errors li").size() > 3) {
        $("#errors li:first").fadeOut(2500, function() {
            $(this).remove();
        });
    }
}
$(function() {
    $("#barcodeform").submit(function(e) {
        var barcode = $("#barcode").val();
        $.getJSON("/gls_json_weight", {"barcode": barcode}, gls_json_weight);
        $("#barcode").val("");
        $("barcode").focus();
        e.preventDefault();
    });
    $("#reset").click(function() {
        window.location.replace("/gls");
    });
});
        </script>
        <style>
table, th, td {
    border: 1px solid black;

}
th, td {
    padding: 10px;
}
        </style>
    </head>
    <body>
        <p>
            <ul>
                <li><a href="/">Zurück</a></li>
                <li><a id="reset" href="#">Reset</a></li>
            </ul>
        </p>
        <p>
            <ul id="errors">
            </ul>
        </p>
        <form id="barcodeform">
            <p>
                <input id="barcode" type="text" autofocus="on" autocomplete="off">
            </p>
        </form>
        <p>
            <table id="weights">
                <tr>
                    <th>Datum</th>
                    <th>Barcode</th>
                    <th></th>
                    <th></th>
                    <th>Gewicht (in kg)</th>
                </tr>
            </table>
        </p>
    </body>
</html>
