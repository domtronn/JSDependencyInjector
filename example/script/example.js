require.def("js-dependency-injector/example",
	[			],
						
	// Alternatively, try typing in the classes you want to require in here
	// separating them by a , then press Cmd/Ctrl + Shift + B to update them all
	// at once!
	function () {

		return ({

			init: function () {
				// Try it out on these two classes!!
				// Place your cursor over one of them and hit Cmd/Ctrl + B
				var x = new Image();
				var y = new Container();
			}

		});

	}
);
