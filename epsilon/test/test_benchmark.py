
from epsilon import hotfix
hotfix.require('twisted', 'delayedcall_seconds')
hotfix.require('twisted', 'timeoutmixin_calllater')

import os, io

from twisted.trial import unittest
from twisted.internet import error, base
from twisted.python import failure, filepath

from epsilon.scripts import benchmark

from epsilon import juice


try:
    filepath.FilePath('/proc/diskstats').open().close()
    filepath.FilePath('/proc/self/mounts').open().close()
except IOError:
    hasProc = False
else:
    hasProc = True



class DiskstatTestCase(unittest.TestCase):
    if not hasProc:
        skip = 'epsilon.benchmark requires access to /proc'


    def testDiskLineParser(self):
        """
        Test the parsing of a single line into a single diststat instance.
        """
        s = ("3    0 hda 267481 3913 3944418 1625467 3392405 3781877 58210592 "
             "150845143 0 6136300 153333793")
        device, stat = benchmark.parseDiskStatLine(s)
        self.assertEqual(device, 'hda')
        self.assertEqual(stat.readCount, 267481)
        self.assertEqual(stat.mergedReadCount, 3913)
        self.assertEqual(stat.readSectorCount, 3944418)
        self.assertEqual(stat.readMilliseconds, 1625467)
        self.assertEqual(stat.writeCount, 3392405)
        self.assertEqual(stat.mergedWriteCount, 3781877)
        self.assertEqual(stat.writeSectorCount, 58210592)
        self.assertEqual(stat.writeMilliseconds, 150845143)
        self.assertEqual(stat.outstandingIOCount, 0)
        self.assertEqual(stat.ioMilliseconds, 6136300)
        self.assertEqual(stat.weightedIOMilliseconds, 153333793)


    def testPartitionLineParser(self):
        """
        Test parsing the other kind of line that can show up in the diskstats
        file.
        """
        s = "3    1 hda1 2 5 7 9"
        device, stat = benchmark.parseDiskStatLine(s)
        self.assertEqual(device, 'hda1')
        self.assertEqual(stat.readCount, 2)
        self.assertEqual(stat.readSectorCount, 5)
        self.assertEqual(stat.writeCount, 7)
        self.assertEqual(stat.writeSectorCount, 9)


    def testFileParser(self):
        """
        Test the parsing of multiple lines into a dict mapping device names and
        numbers to diststat instances.
        """
        s = io.StringIO(
            "1 2 abc 3 4 5 6 7 8 9 10 11 12 13\n"
            "14 15 def 16 17 18 19 20 21 22 23 24 25 26\n")
        ds = list(benchmark.parseDiskStats(s))
        ds.sort()
        self.assertEqual(ds[0][0], "abc")
        self.assertEqual(ds[0][1].readCount, 3)
        self.assertEqual(ds[0][1].mergedReadCount, 4)
        self.assertEqual(ds[0][1].readSectorCount, 5)
        self.assertEqual(ds[0][1].readMilliseconds, 6)
        self.assertEqual(ds[0][1].writeCount, 7)
        self.assertEqual(ds[0][1].mergedWriteCount, 8)
        self.assertEqual(ds[0][1].writeSectorCount, 9)
        self.assertEqual(ds[0][1].writeMilliseconds, 10)
        self.assertEqual(ds[0][1].outstandingIOCount, 11)
        self.assertEqual(ds[0][1].ioMilliseconds, 12)
        self.assertEqual(ds[0][1].weightedIOMilliseconds, 13)

        self.assertEqual(ds[1][0], "def")
        self.assertEqual(ds[1][1].readCount, 16)
        self.assertEqual(ds[1][1].mergedReadCount, 17)
        self.assertEqual(ds[1][1].readSectorCount, 18)
        self.assertEqual(ds[1][1].readMilliseconds, 19)
        self.assertEqual(ds[1][1].writeCount, 20)
        self.assertEqual(ds[1][1].mergedWriteCount, 21)
        self.assertEqual(ds[1][1].writeSectorCount, 22)
        self.assertEqual(ds[1][1].writeMilliseconds, 23)
        self.assertEqual(ds[1][1].outstandingIOCount, 24)
        self.assertEqual(ds[1][1].ioMilliseconds, 25)
        self.assertEqual(ds[1][1].weightedIOMilliseconds, 26)


    def testCaptureStats(self):
        """
        Test that captureStats reads out of /proc/diskstats, if it is
        available.
        """
        stats = benchmark.captureStats()
        self.assertTrue(isinstance(stats, dict), "Expected dictionary, got %r" % (stats,))



class ReporterTestCase(unittest.TestCase):
    def testFormatter(self):
        [msg] = juice.parseString(benchmark.formatResults(
            "frunk",
            4096,
            benchmark.ResourceSnapshot(
                3,
                benchmark.diskstat(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
                benchmark.partitionstat(1, 2, 3, 4),
                12),
            benchmark.ResourceSnapshot(
                7,
                benchmark.diskstat(11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21),
                benchmark.partitionstat(5, 7, 9, 11),
                56), False, False))

        self.assertEqual(msg['_command'], 'Result')

        self.assertEqual(msg['version'], '0')
        self.assertEqual(msg['error'], 'False')
        self.assertEqual(msg['timeout'], 'False')
        self.assertEqual(msg['name'], 'frunk')
        self.assertNotEqual(msg['host'], 'localhost')

        self.assertIn('sector_size', msg)
        self.assertIn('python_version', msg)
        self.assertIn('twisted_version', msg)
        self.assertIn('divmod_version', msg)

        self.assertEqual(msg['elapsed'], '4')
        self.assertEqual(msg['filesystem_growth'], '44')
        self.assertEqual(msg['read_count'], '4')
        self.assertEqual(msg['read_sectors'], '5')
        self.assertEqual(msg['write_count'], '6')
        self.assertEqual(msg['write_sectors'], '7')
        self.assertEqual(msg['read_ms'], '10')
        self.assertEqual(msg['write_ms'], '10')


    def testFormatterWithoutDiskStats(self):
        """
        Sometimes it is not possible to find diskstats.  In these cases, None
        should be reported as the value for all fields which are derived from
        the diskstats object.
        """
        [msg] = juice.parseString(benchmark.formatResults(
            "frunk",
            4096,
            benchmark.ResourceSnapshot(
                3,
                None,
                benchmark.partitionstat(1, 2, 3, 4),
                12),
            benchmark.ResourceSnapshot(
                7,
                None,
                benchmark.partitionstat(5, 7, 9, 11),
                56), False, False))

        self.assertEqual(msg['_command'], 'Result')

        self.assertEqual(msg['version'], '0')
        self.assertEqual(msg['error'], 'False')
        self.assertEqual(msg['timeout'], 'False')
        self.assertEqual(msg['name'], 'frunk')
        self.assertNotEqual(msg['host'], 'localhost')

        self.assertIn('sector_size', msg)
        self.assertIn('python_version', msg)
        self.assertIn('twisted_version', msg)
        self.assertIn('divmod_version', msg)

        self.assertEqual(msg['elapsed'], '4')
        self.assertEqual(msg['filesystem_growth'], '44')
        self.assertEqual(msg['read_count'], '4')
        self.assertEqual(msg['read_sectors'], '5')
        self.assertEqual(msg['write_count'], '6')
        self.assertEqual(msg['write_sectors'], '7')

        self.failIfIn('read_ms', msg)
        self.failIfIn('write_ms', msg)


    def testFormatterWithoutPartitionStats(self):
        """
        Sometimes it is not possible to find partitionstats.  In these cases,
        None should be reported as the value for all fields which are derived
        from the partitionstats object.
        """
        [msg] = juice.parseString(benchmark.formatResults(
            "frunk",
            4096,
            benchmark.ResourceSnapshot(
                3,
                benchmark.diskstat(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
                None,
                12),
            benchmark.ResourceSnapshot(
                7,
                benchmark.diskstat(11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21),
                None,
                56), False, False))

        self.assertEqual(msg['_command'], 'Result')

        self.assertEqual(msg['version'], '0')
        self.assertEqual(msg['error'], 'False')
        self.assertEqual(msg['timeout'], 'False')
        self.assertEqual(msg['name'], 'frunk')
        self.assertNotEqual(msg['host'], 'localhost')

        self.assertIn('sector_size', msg)
        self.assertIn('python_version', msg)
        self.assertIn('twisted_version', msg)
        self.assertIn('divmod_version', msg)

        self.assertEqual(msg['elapsed'], '4')
        self.assertEqual(msg['filesystem_growth'], '44')

        self.failIfIn('read_count', msg)
        self.failIfIn('read_sectors', msg)
        self.failIfIn('write_count', msg)
        self.failIfIn('write_sectors', msg)

        self.assertEqual(msg['read_ms'], '10')
        self.assertEqual(msg['write_ms'], '10')


    def testGetSize(self):
        path = self.mktemp()
        os.makedirs(path)
        fObj = file(os.path.join(path, 'foo'), 'wb')
        fObj.write('x' * 10)
        fObj.close()
        self.assertEqual(
            benchmark.getSize(filepath.FilePath(path)),
            os.path.getsize(path) + os.path.getsize(os.path.join(path, 'foo')))


    def test_getOneSizeBrokenSymlink(self):
        """
        Test that a broken symlink inside a directory passed to getOneSize doesn't
        cause it to freak out.
        """
        path = filepath.FilePath(self.mktemp())
        path.makedirs()
        link = path.child('foo')
        os.symlink('abcdefg', link.path)
        self.assertEqual(
            benchmark.getOneSize(link),
            len('abcdefg'))



class MockSpawnProcess(object):
    """
    A fake partial ITransport implementation for use in testing
    ProcessProtocols.
    """

    killed = False

    def __init__(self, proto, executable, args, path, env, childFDs):
        self.proto = proto
        self.executable = executable
        self.args = args
        self.path = path
        self.env = env
        self.childFDs = childFDs
        self.signals = []


    def signalProcess(self, signal):
        self.signals.append(signal)
        if signal == 'KILL':
            self.killed = True
            self.proto.processEnded(failure.Failure(error.ProcessTerminated()))



class SpawnMixin:

    def setUp(self):
        mock = []
        def spawnProcess(*a, **kw):
            mock.append(MockSpawnProcess(*a, **kw))
            return mock[0]
        self.workingDirectory = self.mktemp()
        os.makedirs(self.workingDirectory)
        self.spawnDeferred = self.processProtocol.spawn(
            'executable', ['args'], self.workingDirectory, {'env': 'stuff'},
            spawnProcess)
        self.mock = mock[0]

        self.sched = []
        self.currentTime = 0

        def seconds():
            return self.currentTime

        def canceller(c):
            self.sched.remove(c)

        def resetter(c):
            self.sched.sort(key=lambda d: d.getTime())

        def callLater(n, f, *a, **kw):
            c = base.DelayedCall(self.currentTime + n, f, a, kw, canceller, resetter, seconds)
            self.sched.append(c)
            return c

        self.mock.proto.callLater = callLater
        self.mock.proto.makeConnection(self.mock)



class BasicProcessTestCase(SpawnMixin, unittest.TestCase):
    processProtocol = benchmark.BasicProcess

    def testCorrectArgs(self):
        self.assertEqual(self.mock.executable, 'executable')
        self.assertEqual(self.mock.args, ['executable', 'args'])
        self.assertEqual(self.mock.path, self.workingDirectory)
        self.assertEqual(self.mock.env, {'env': 'stuff'})


    def testChildDataReceived(self):
        self.mock.proto.childDataReceived(1, 'stdout bytes')
        self.mock.proto.childDataReceived(2, 'stderr bytes')
        self.mock.proto.childDataReceived(1, 'more stdout bytes')

        def cbProcessFinished(xxx_todo_changeme):
            (proto, status, output) = xxx_todo_changeme
            self.assertIdentical(proto, self.mock.proto)
            self.assertEqual(status, 0)
            self.assertEqual(
                output,
                [(1, 'stdout bytes'),
                 (2, 'stderr bytes'),
                 (1, 'more stdout bytes')])
        self.spawnDeferred.addCallback(cbProcessFinished)
        self.mock.proto.processEnded(failure.Failure(error.ProcessDone(0)))
        return self.spawnDeferred


    def testTimeout(self):
        """
        Assert that a timeout call is created as soon as the process is started
        and that if it expires, the spawn call's Deferred fails.
        """
        self.assertEqual(len(self.sched), 1)
        self.assertEqual(self.sched[0].getTime(), 900.0)
        self.sched[0].func(*self.sched[0].args, **self.sched[0].kw)

        def cbTimedOut(ign):
            self.assertEqual(self.mock.signals, ['KILL'])

        d = self.assertFailure(self.spawnDeferred, error.TimeoutError)
        d.addCallback(cbTimedOut)
        return d


    def testTimeoutExtended(self):
        """
        Assert that input or connection-lost events reset the timeout.
        """
        self.currentTime = 1
        self.mock.proto.childDataReceived(1, 'bytes')
        self.assertEqual(len(self.sched), 1)
        self.assertEqual(self.sched[0].getTime(), 901.0)

        self.currentTime = 2
        self.mock.proto.childConnectionLost(1)
        self.assertEqual(len(self.sched), 1)
        self.assertEqual(self.sched[0].getTime(), 902.0)


    def testProcessKilled(self):
        """
        Assert that the spawn call's Deferred fails appropriately if someone
        else gets involved and kills the child process.
        """
        def cbKilled(exc):
            self.assertEqual(exc.exitCode, 1)
            self.assertEqual(exc.signal, 2)
            self.assertEqual(exc.status, 3)
            self.assertEqual(exc.output, [(1, 'bytes')])

        self.mock.proto.childDataReceived(1, 'bytes')
        self.mock.proto.processEnded(failure.Failure(error.ProcessTerminated(1, 2, 3)))
        d = self.assertFailure(self.spawnDeferred, benchmark.ProcessDied)
        d.addCallback(cbKilled)
        return d



class SnapshotTestCase(unittest.TestCase):
    if not hasProc:
        skip = 'epsilon.benchmark requires access to /proc'


    def testStart(self):
        c = benchmark.Change()
        c.start(filepath.FilePath('.'), 'hda', 'hda1')
        self.assertTrue(isinstance(c.before, benchmark.ResourceSnapshot))


    def testStop(self):
        c = benchmark.Change()
        c.stop(filepath.FilePath('.'), 'hda', 'hda1')
        self.assertTrue(isinstance(c.after, benchmark.ResourceSnapshot))



class BenchmarkProcessTestCase(SpawnMixin, unittest.TestCase):
    if not hasProc:
        skip = 'epsilon.benchmark requires access to /proc'


    processProtocol = benchmark.BenchmarkProcess

    def testProcessStartTimingCommand(self):
        started = []
        p = self.mock.proto
        p.startTiming = lambda: started.append(None)
        self.mock.proto.childDataReceived(p.BACKCHANNEL_OUT, p.START)
        self.assertEqual(started, [None])


    def testProcessStopTimingCommand(self):
        stopped = []
        p = self.mock.proto
        p.stopTiming = lambda: stopped.append(None)
        self.mock.proto.childDataReceived(p.BACKCHANNEL_OUT, p.STOP)
        self.assertEqual(stopped, [None])
