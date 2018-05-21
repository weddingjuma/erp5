/*global window, rJS, RSVP, jIO */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP, jIO) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("notifySubmitting", "notifySubmitting")
    .declareAcquiredMethod("jio_post", "jio_post")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("jio_putAttachment", "jio_putAttachment")
    .declareAcquiredMethod("redirect", "redirect")
    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////

    .allowPublicAcquisition('submitContent', function () {
      var gadget = this,
        file_name,
        jio_key,
        data,
        format;

      return gadget.notifySubmitting()
        .push(function () {
          return gadget.getDeclaredGadget('form_view');
        })
        .push(function (form_gadget) {
          return RSVP.all([
            form_gadget.getContent(),
            gadget.getSetting('portal_type'),
            gadget.getSetting('content_type')
          ]);
        })
        .push(function (result) {
          format = result[0].format;
          file_name = result[0].file.file_name.split(format)[0];
          data = jIO.util.dataURItoBlob(result[0].file.url);
          return gadget.jio_post({
            title: file_name,
            portal_type: result[1],
            content_type: result[2],
            filename: file_name
          });
        })
        .push(function (doc_id) {
          jio_key = doc_id;
          return gadget.jio_putAttachment(jio_key, "data?" + format, data);
        })
        .push(function () {
          return gadget.redirect({command: 'display', options: {jio_key: jio_key}});
        });
    })

    .declareMethod("triggerSubmit", function () {
      return this.element.querySelector('button[type="submit"]').click();
    })

    .declareMethod("render", function () {
      var gadget = this;
      return gadget.getSetting('upload_extension')
        .push(function (upload_extension) {
          return gadget.changeState({
            upload_extension: upload_extension
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
                "my_file": {
                  "description": "",
                  "title": "File",
                  "default": "",
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "file",
                  "hidden": 0,
                  "type": "FileField"
                },
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
              title: "Upload",
              group_list: [[
                "center",
                [["my_file"], ["my_format"]]
              ]]
            }
          });
        })
        .push(function () {
          return gadget.getUrlFor({command: 'display', options: {page: 'ojs_document_list'}});
        })
        .push(function (url) {
          return gadget.updateHeader({
            page_title: "Upload File",
            selection_url: url
          });
        });
    });
}(window, rJS, RSVP, jIO));