/*global window, rJS, RSVP, jIO, document, URL */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP, jIO, document, URL) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("jio_getAttachment", "jio_getAttachment")
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("notifySubmitting", "notifySubmitting")
    .declareAcquiredMethod("notifySubmitted", 'notifySubmitted')
    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////

    .declareMethod("render", function (options) {
      var gadget = this;
      return new RSVP.Queue()
        .push(function () {
          return RSVP.all([
            gadget.getSetting('upload_extension'),
            gadget.getSetting('file_extension')
          ]);
        })
        .push(function (result) {
          return gadget.changeState({
            jio_key: options.jio_key,
            upload_extension: result[0],
            file_extension: result[1]
          });
        });
    })

    .onStateChange(function () {
      var gadget = this;
      return gadget.getDeclaredGadget('form_view')
        .push(function (form_gadget) {
          return form_gadget.render({
            erp5_document: {
              "_embedded": {"_view": {
                "_actions": {"put": {}},
                "form_id": {},
                "dialog_id": {},
                "my_format": {
                  "title": "Format",
                  "default": gadget.state.upload_extension,
                  "key": "format",
                  "first_item": 0,
                  "items": [gadget.state.upload_extension],
                  "editable": 1,
                  "type": "ListField"
                }
              }},
              "_links": {
                "type": {
                  // form_list display portal_type in header
                  name: ""
                }
              }
            },
            form_definition: {
              title: "Download",
              group_list: [[
                "center",
                [["my_format"]]
              ]]
            }
          });
        })
        .push(function () {
          return RSVP.all([
            gadget.getUrlFor({command: 'history_previous'}),
            gadget.getUrlFor({command: 'selection_previous'}),
            gadget.getUrlFor({command: 'selection_next'})
          ]);
        })
        .push(function (url_list) {
          return gadget.updateHeader({
            page_title: "Download File",
            selection_url: url_list[0],
            previous_url: url_list[1],
            next_url: url_list[2]
          });
        });
    })

    .allowPublicAcquisition('submitContent', function () {
      var gadget = this, format;

      return gadget.notifySubmitting()
        .push(function () {
          return gadget.getDeclaredGadget('form_view');
        })
        .push(function (form_gadget) {
          return form_gadget.getContent();
        })
        .push(function (content) {
          format = content.format;
          return RSVP.all([
            gadget.jio_getAttachment(gadget.state.jio_key, 'data?' + format),
            gadget.jio_get(gadget.state.jio_key)
          ]);
        })
        .push(function (result) {
          var a = document.createElement('a'),
             url = URL.createObjectURL(result[0]);
          a.href = url;
          a.download = result[1].filename.split(
            gadget.state.file_extension
          )[0] +  format;
          gadget.element.appendChild(a);
          a.click();
          gadget.element.removeChild(a);
          URL.revokeObjectURL(url);
          return gadget.notifySubmitted();
        })
        .push(function () {
          return gadget.redirect({
            command: "display",
            options: {jio_key: gadget.state.jio_key}
          });
        });
    });
}(window, rJS, RSVP, jIO, document, URL));