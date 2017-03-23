/*jslint nomen: true, indent: 2, maxerr: 3, maxlen: 80*/
/*globals window, RSVP, rJS, jIO*/
(function (window, RSVP, rJS, jIO) {
  "use strict";


  /* Initialization */

  rJS(window)

    .ready(function () {
      var gadget = this;
      return gadget.changeState({
        storage: jIO.createJIO({
          type: "query",
          sub_storage: {
            type: "uuid",
            sub_storage: {
              type: "document",
              document_id: "/",
              sub_storage: {
                type: "local"
              }
            }
          }
        })
      });
    })


    /* Declared Methods */

    .declareMethod("postTodo", function (title) {
      var gadget = this,
        storage = gadget.state.storage;
      return storage.post({
        title: title,
        completed: false,
        creation_date: Date.now()
      });
    })

    .declareMethod("putTodo", function (id, todo) {
      var gadget = this,
        storage = gadget.state.storage;
      return storage.get(id)
        .push(function (result) {
          var key;
          for (key in todo) {
            if (todo.hasOwnProperty(key)) {
              result[key] = todo[key];
            }
          }
          return result;
        }, function () {
          return todo;
        })
        .push(function (todo) {
          return storage.put(id, todo);
        });
    })

    .declareMethod("getTodos", function (query) {
      var gadget = this,
        storage = gadget.state.storage;
      return storage.allDocs({
        query: query,
        sort_on: [["creation_date", "ascending"]],
        select_list: ["title", "completed"]
      })
        .push(function (result_list) {
          var todo_list = [], todo, i;
          for (i = 0; i < result_list.data.total_rows; i += 1) {
            todo = result_list.data.rows[i];
            todo_list.push({
              id: todo.id,
              title: todo.value.title,
              completed: todo.value.completed
            });
          }
          return todo_list;
        });
    })

    .declareMethod("getTodoCountDict", function () {
      var gadget = this,
        storage = gadget.state.storage;
      return storage.allDocs({select_list: ["completed"]})
        .push(function (result_list) {
          var todo_count_dict = {
            total: result_list.data.total_rows,
            active: 0
          }, i;
          for (i = 0; i < result_list.data.total_rows; i += 1) {
            if (!result_list.data.rows[i].value.completed) {
              todo_count_dict.active += 1;
            }
          }
          return todo_count_dict;
        });
    })

    .declareMethod("changeTitle", function (id, title) {
      var gadget = this;
      return gadget.putTodo(id, {title: title});
    })

    .declareMethod("toggleOne", function (id, completed) {
      var gadget = this;
      return gadget.putTodo(id, {completed: completed});
    })

    .declareMethod("toggleAll", function (completed) {
      var gadget = this,
        storage = gadget.state.storage;
      return storage.allDocs()
        .push(function (result_list) {
          var promise_list = [], i;
          for (i = 0; i < result_list.data.total_rows; i += 1) {
            promise_list.push(
              gadget.toggleOne(result_list.data.rows[i].id, completed)
            );
          }
          return RSVP.all(promise_list);
        });
    })

    .declareMethod("removeOne", function (id) {
      var gadget = this,
        storage = gadget.state.storage;
      return storage.remove(id);
    })

    .declareMethod("removeCompleted", function () {
      var gadget = this;
      return gadget.getTodos()
        .push(function (todo_list) {
          var promise_list = [], i;
          for (i = 0; i < todo_list.length; i += 1) {
            if (todo_list[i].completed) {
              promise_list.push(gadget.removeOne(todo_list[i].id));
            }
          }
          return RSVP.all(promise_list);
        });
    });

}(window, RSVP, rJS, jIO));