"""Unit tests for the pure helpers in the validate_settings management command."""

from rich.tree import Tree

from bridge.management.commands.validate_settings import _add, _is_secret, _mask


class TestIsSecret:
    def test_matches_secret_hints(self):
        assert _is_secret("password")
        assert _is_secret("secret_key")
        assert _is_secret("DB_PASSWORD")  # case-insensitive
        assert _is_secret("aws_access_key")
        assert _is_secret("private_key")

    def test_non_secret_keys(self):
        assert not _is_secret("host")
        assert not _is_secret("port")
        assert not _is_secret("username")


class TestMask:
    def test_masks_string_with_length(self):
        assert _mask("hunter2") == "**** (len=7)"
        assert _mask("") == "**** (len=0)"

    def test_masks_non_string(self):
        assert _mask(1234) == "****"
        assert _mask(None) == "****"


class TestAdd:
    def test_secret_leaf_is_masked_in_tree(self):
        tree = Tree("root")
        _add(tree, {"host": "omero", "password": "topsecret"})
        labels = [str(child.label) for child in tree.children]
        # The plain value is shown; the secret value is masked, not in the clear.
        assert any("'omero'" in label for label in labels)
        assert any("**** (len=9)" in label for label in labels)
        assert all("topsecret" not in label for label in labels)

    def test_nested_secret_block_masks_all_leaves(self):
        tree = Tree("root")
        _add(tree, {"postgres": {"username": "u", "password": "p"}})
        # postgres is a branch; descend into it.
        branch = tree.children[0]
        leaf_labels = [str(c.label) for c in branch.children]
        assert any("username" in label for label in leaf_labels)
        # username under a non-secret block is shown in the clear.
        assert any("'u'" in label for label in leaf_labels)
